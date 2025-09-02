import React from 'react';
import Image from "next/image";
import logo from "../../app/auth/logo.png"

const Logo: React.FC = () => {
    return (
        <header className="flex flex-col justify-center items-start p-8 max-md:px-5 max-md:max-w-full">
            <Image src={logo} alt={"logo"} width={150} />
        </header>
    );
}

export default Logo;