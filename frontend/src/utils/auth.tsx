import { ACCESS_TOKEN, REFRESH_TOKEN } from "@/constants";
import { decodeJWT } from "./jwt";
import Cookies from "js-cookie";
import { setCookie } from "cookies-next";

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

  return accessToken;
}

export const isAuthenticated = () => {
  const accessToken = Cookies.get(ACCESS_TOKEN);
  const refreshToken = Cookies.get(REFRESH_TOKEN);
  if (accessToken && refreshToken) return true;
  return false;
};



export const setToken = async (LogInData: any) => {
  const TENANT_ID = "clickshow_tenant_id";

  const decoded = decodeJWT(LogInData["access_token"]);
  Cookies.set(ACCESS_TOKEN, LogInData["access_token"], {
    expires: new Date(decoded.exp * 1000),
  });
  Cookies.set(REFRESH_TOKEN, LogInData["refresh_token"], {
    expires: new Date(decoded.exp * 1000),
  });
  Cookies.set("member_id", LogInData?.['memberships']?.[0]?.["member_id"], {
    expires: new Date(decoded.exp * 1000),
  });

  Cookies.set("login_data", JSON.stringify(LogInData), {
    expires: new Date(decoded.exp * 1000),
  });
  setCookie(
    TENANT_ID,
    LogInData["memberships"].length
      ? LogInData["memberships"]?.[0]?.["organisation_id"]
      : "",
    {
      expires: new Date(decoded.exp * 1000),
    }
  );

  Cookies.set(
    TENANT_ID,
    LogInData["memberships"].length
      ? LogInData["memberships"]?.[0]?.["organisation_id"]
      : "",
    {
      expires: new Date(decoded.exp * 1000),
    }
  );

  return LogInData;
};