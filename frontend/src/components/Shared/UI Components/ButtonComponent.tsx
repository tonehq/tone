'use client';

import { Button } from 'antd';
import type { ButtonProps as AntdButtonProps } from 'antd';
import { ChevronRight, LucideIcon } from 'lucide-react';

interface ButtonProps {
  icon?: LucideIcon | React.ReactNode;
  text?: string;
  onClick?: () => void;
  active?: boolean;
  disabled?: boolean;
  className?: string;
  loading?: boolean;
  type?: 'primary' | 'default' | 'dashed' | 'link' | 'text';
  htmlType?: AntdButtonProps['htmlType'];
}

const ButtonComponent = ({
  icon: Icon,
  text,
  onClick,
  type,
  active,
  disabled,
  className,
  loading,
  htmlType,
}: ButtonProps) => (
  <>
    {Icon === ChevronRight ? (
      <Button
        type={type ? type : 'default'}
        style={{
          height: '36px',
          borderRadius: '5px',
          fontWeight: 500,
          textAlign: 'center',
          background: active ? '#1D4ED8' : '',
          color: active ? 'white' : '#334155',
        }}
        className={`border-slate-200 !outline-none !ring-0 !shadow-none h-9  bg-white text-sm text-slate-700 hover:bg-slate-50 ${className}`}
        onClick={onClick}
        disabled={disabled}
        loading={loading}
        htmlType={htmlType}
      >
        {text && text}
        {Icon && <Icon className="w-4 h-4 font-semibold" />}
      </Button>
    ) : (
      <Button
        type={type ? type : 'default'}
        style={{
          height: '36px',
          borderRadius: '5px',
          textAlign: 'center',
          background: active ? '#1D4ED8' : '',
          color: active ? 'white' : '#334155',
        }}
        className={`border-slate-200 !outline-none !ring-0 !shadow-none h-9  bg-white text-sm text-slate-700 hover:bg-slate-50 ${className}`}
        onClick={onClick}
        disabled={disabled}
        htmlType={htmlType}
        loading={loading}
      >
        {Icon &&
          (typeof Icon === 'function' ? (
            <Icon className="w-4 h-4 font-semibold" />
          ) : (
            <span className="w-4 h-4 font-semibold">{Icon}</span>
          ))}
        {text && text}
      </Button>
    )}
  </>
);

export default ButtonComponent;
