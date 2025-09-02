import "./globals.scss";
import Head from "next/head";
import { ConfigProvider } from "antd";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
      <ConfigProvider
        theme={{
          token: {
            colorPrimary: "#4058ff", 
            colorSuccess: "#52c41a", 
            colorWarning: "#faad14", 
            colorBorder: "#F9F8F8"
          },
        }}
      >
       
            <div>{children}</div>
          
      </ConfigProvider>
      </body>
    </html>
  );
}
