import React from 'react'

interface AnimatedInputFieldProps {
    text: string;
}

const ButtonField: React.FC<AnimatedInputFieldProps> = ({
    text
}) => {
    return (
        <button className=" relative w-64 h-14 bg-purple-500 text-white font-bold text-lg rounded-full  overflow-hidden focus:outline-none transition-all duration-300 ease-in-out hover:scale-105 active:scale-95 group">
            {/* Hover background */}
            <div className=" absolute inset-0 bg-purple-600  transition-all duration-300 ease-in-out opacity-0 scale-0 group-hover:opacity-100 group-hover:scale-100" />

            {/* Active background */}
            <div className=" absolute inset-0 bg-purple-700 transition-all duration-200 ease-in-out opacity-0 scale-0 group-active:opacity-100 group-active:scale-100" />

            {/* Button text */}
            <span className=" relative z-10 flex justify-center inline-block transition-transform duration-200 ease-in-out group-active:translate-y-0.5">
                {text}
            </span>

            {/* Hover border */}
            <div className=" absolute inset-0 border-2 border-white rounded-full  transition-all duration-300 ease-in-out opacity-0 scale-90 group-hover:opacity-100 group-hover:scale-100 " />
        </button>
    )
}

export default ButtonField
