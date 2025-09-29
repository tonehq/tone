import React, { ReactNode } from 'react';

import { Layout } from 'antd';

const { Sider, Content } = Layout;

interface CustomLayoutProps {
  sidebarContent: ReactNode;
  children: ReactNode;
  siderWidth?: number | string;
  layoutStyle?: React.CSSProperties;
  siderStyle?: React.CSSProperties;
}

const CustomLayout: React.FC<CustomLayoutProps> = ({
  sidebarContent,
  children,
  siderWidth = 200,
  layoutStyle,
  siderStyle,
}) => {
  const defaultLayoutStyle: React.CSSProperties = {
    width: '100%',
    minHeight: '100%',
    padding: 16,
    ...layoutStyle,
  };

  const defaultSiderStyle: React.CSSProperties = {
    borderRadius: 8,
    padding: 16,
    color: 'white',
    minHeight: '100%',
    marginInline: 8,
    ...siderStyle,
  };

  const defaultContentStyle: React.CSSProperties = {
    paddingInline: 24,
  };

  return (
    <Layout style={defaultLayoutStyle}>
      <Sider width={siderWidth} style={defaultSiderStyle}>
        {sidebarContent}
      </Sider>
      <Content style={defaultContentStyle}>{children || 'testing'}</Content>
    </Layout>
  );
};

export default CustomLayout;
