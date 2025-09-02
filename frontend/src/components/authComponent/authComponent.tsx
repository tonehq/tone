import React from 'react';
import Logo from './Logo';
// import Image from "next/image";
// import logo from "../../app/auth/logo.png"
import Footer from './Footer';
import Testimonial from './Testimonial';

const AuthComponent = (props: any) => {

    return (
        <main className="flex flex-col justify-center bg-white h-[100vh]">
            <div className="w-full bg-white max-md:max-w-full h-full">
                <div className="flex gap-5 max-md:flex-col h-full">
                    <section className="flex flex-col w-6/12 max-md:ml-0 max-md:w-full">
                        <div className="flex flex-col grow max-md:max-w-full">
                            <div className='h-[10%]'>
                                {/* <Image src={logo} alt={"logo"} width={150} /> */}
                                <Logo />
                            </div>
                            <div className='h-[80%] flex items-center justify-center'>
                                {props.children}
                            </div>
                            <div className='h-[10%]'>
                                <Footer />
                            </div>
                        </div>
                    </section>
                    <Testimonial />
                </div>
            </div>
        </main>
    );
};

export default AuthComponent;