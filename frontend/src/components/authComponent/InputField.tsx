"use client"

import React, { useState, ChangeEvent, FocusEvent } from 'react';

interface AnimatedInputFieldProps {
    label: string;
    type?: 'text' | 'email' | 'password' | 'number';
    id: string;
    name: string;
    required?: boolean;
}

const AnimatedInputField: React.FC<AnimatedInputFieldProps> = ({
    label,
    type = 'text',
    id,
    name,
    required = false,
}) => {
    const [isFocused, setIsFocused] = useState<boolean>(false);
    const [value, setValue] = useState<string>('');

    const handleFocus = (): void => setIsFocused(true);
    const handleBlur = (): void => setIsFocused(false);
    const handleChange = (e: ChangeEvent<HTMLInputElement>): void => setValue(e.target.value);

    return (
        <div className="relative mb-4">
            <input
                type={type}
                id={id}
                name={name}
                required={required}
                className="peer w-full h-10 border-b-2 border-gray-300 text-gray-900 placeholder-transparent focus:outline-none focus:border-purple-600 transition-colors duration-300"
                placeholder={label}
                value={value}
                onChange={handleChange}
                onFocus={handleFocus}
                onBlur={handleBlur}
            />
            <label
                htmlFor={id}
                className={`absolute left-0 -top-3.5 text-gray-600 text-sm transition-all duration-300 
                    ${(isFocused || value)
                        ? '-top-3.5 text-sm text-purple-600'
                        : 'top-2 text-base'}`}
            >
                {label}
            </label>
        </div>
    );
};

export default AnimatedInputField