import { message, notification } from "antd";
import React from "react";

export type ToastStatus = "success" | "error" | "info" | "warning";
export type ToastVariant = "notification" | "message";

let notificationApi: ReturnType<typeof notification.useNotification>[0];
let messageApi: ReturnType<typeof message.useMessage>[0];

export function initToast() {
  const [nApi, nHolder] = notification.useNotification();
  const [mApi, mHolder] = message.useMessage();

  notificationApi = nApi;
  messageApi = mApi;

  // must be rendered once in App root
  return (
    <>
      {nHolder}
      {mHolder}
    </>
  );
}

export interface ShowToastConfig {
  status: ToastStatus;
  message: string;
  description?: string;
  duration?: number;
  placement?: "topRight" | "topLeft" | "top" | "bottomRight" | "bottomLeft" | "bottom";
  variant?: ToastVariant; // notification or message
  style?: React.CSSProperties; // only for message variant
}

export function showToast({
  status,
  message: msg,
  description = "",
  duration = 3,
  placement = "bottomRight",
  variant = "notification", // default
  style
}: ShowToastConfig) {
  if (variant === "notification") {
    if (!notificationApi) {
      console.error("⚠️ initToast() not initialized. Call it in App root.");
      return;
    }

    // ensure only one visible at a time
    notificationApi.destroy();
    notificationApi[status]({
      message: msg,
      description,
      duration,
      placement,
      style
    });
  } else {
    if (!messageApi) {
      console.error("⚠️ initToast() not initialized. Call it in App root.");
      return;
    }

    // ensure only one message visible
    messageApi.destroy();
    messageApi.open({
      type: status,
      content: description ? `${msg} - ${description}` : msg,
      duration,
      style,
    });
  }
}
