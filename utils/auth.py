from fastapi.responses import RedirectResponse
from fastapi.routing import APIRouter
from fastapi.security import APIKeyCookie
from fastapi import Depends, Response, Request
from ..config import ASYNC_REQUESTS_CLIENT, AVATAR_URL, AUTH_URL
from datetime import timedelta
from time import time


COOKIE_SCHEME = APIKeyCookie(name="access_token")


async def get_logged_user(access_token: str = Depends(COOKIE_SCHEME)):
	request = await ASYNC_REQUESTS_CLIENT.get(f"{AUTH_URL}/authorization/validate?token={access_token}", verify=False)
	if request.status > 299:
		return False
	request = await ASYNC_REQUESTS_CLIENT.get(f"{AUTH_URL}/authorization/getClaims?token={access_token}", verify=False)
	response = await request.json()
	response["avatar"] = f"{AVATAR_URL}/{response['sAMAccountName']}"
	return response


router = APIRouter(tags=["Auth"], prefix="/auth")


@router.get("/login")
async def login():
	return RedirectResponse("/authentication?tokenConsumerURL=/auth/me")


@router.get("/me", include_in_schema=False)
async def get_user(request: Request, response: Response, token=""):
	user = await get_logged_user(token)
	if user:
		response.set_cookie(key="access_token", value=token, expires=timedelta(user["exp"] - 48 - int(time())), httponly=True)
		response.status_code = 387
		response.headers["Location"] = "/"
		return True
	if "access_token" not in request.cookies.keys():
		return RedirectResponse('/login')
	return await get_logged_user(request.cookies["access_token"])


@router.get("/auth_example")
async def example_auth_required_endpoint(current_user=Depends(get_logged_user)):
	return current_user