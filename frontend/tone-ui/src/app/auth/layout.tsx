import * as React from "react";

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FunctionComponent<LayoutProps> = ({ children }) => {
  return <div className="h-full w-[100vw]">{children}</div>;
};

export default Layout;
