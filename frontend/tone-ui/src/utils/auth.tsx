import { ACCESS_TOKEN, REFRESH_TOKEN } from "@/constants";
import { decodeJWT } from "./jwt";
import Cookies from "js-cookie";

export async function getToken() {
  let accessToken = Cookies.get(ACCESS_TOKEN);
  const refreshToken = Cookies.get(REFRESH_TOKEN);

  if (!refreshToken) return null;

  if (!accessToken && refreshToken) {
    const res = await fetch(`${process.env["APP_API"]}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    const tokens = await res.json();

    if (!tokens) return null;

    const accessClaims = decodeJWT(tokens["access_token"]);
    Cookies.set(ACCESS_TOKEN, tokens["access_token"], {
      expires: new Date(accessClaims.exp * 1000),
    });
    accessToken = tokens["access_token"];
  }

  console.log("accessToken", accessToken);

  return accessToken;
}

export const isAuthenticated = () => {
  const accessToken = Cookies.get(ACCESS_TOKEN);
  const refreshToken = Cookies.get(REFRESH_TOKEN);
  if (accessToken && refreshToken) return true;
  return false;
};
