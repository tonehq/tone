'use client'

import { FC, ComponentType, useEffect } from "react";
import { useRouter } from "next/navigation";
import Cokkies from "js-cookie";
interface WithAuthProps {
  [key: string]: any;
}

const withAuth = <P extends WithAuthProps>(
  WrappedComponent: ComponentType<P>
) => {
  const WithAuthComponent: FC<P> = (props) => {
    const router = useRouter();

    useEffect(() => {
      if (typeof window !== "undefined") {
        const token = Cokkies.get("clickshow_access_token");
        if (!token) {
          router.push("/auth/login");
        }
      }
    }, [router]);

    return <WrappedComponent {...props} />;
  };
  return WithAuthComponent;
};

export default withAuth;
