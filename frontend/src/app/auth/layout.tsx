import * as React from 'react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FunctionComponent<LayoutProps> = ({ children }) => <div>{children}</div>;

export default Layout;
