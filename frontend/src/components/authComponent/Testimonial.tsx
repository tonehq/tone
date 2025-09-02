import React from 'react';

const Testimonial: React.FC = () => {
    return (
        <aside className="flex-col ml-5 w-6/12 max-md:ml-0 max-md:w-full hidden md:flex">
            <div className="flex relative flex-col grow rounded-[80px_0px_0px_80px] max-md:px-5 max-md:max-w-full">
                <img loading="lazy" src="https://cdn.builder.io/api/v1/image/assets/TEMP/064d49d468d0952bd0a54eff0df8fb9a191373a750f515c5d402d20433ce4293?apiKey=99f610f079bc4250a85747146003507a&&apiKey=99f610f079bc4250a85747146003507a" alt="Background image" className="object-cover absolute h-[100vh] inset-0 size-full" />
                <div className='flex flex-col px-8 justify-end h-[100vh]'>
                    <blockquote className="relative text-4xl font-medium tracking-tighter leading-10 text-white max-md:mt-10 max-md:max-w-full mb-8">
                        "We've been using Untitled to kick start every new project and can't imagine working without it."
                    </blockquote>
                    <div className="relative mb-6 text-3xl font-semibold leading-10 text-white max-md:max-w-full">Amélie Laurent</div>
                    {/* <div className="flex relative gap-3 mt-3 max-md:flex-wrap">
                        <div className="flex flex-col flex-1 self-start text-white max-md:max-w-full">
                            <p className="text-lg font-semibold leading-7 max-md:max-w-full">Lead Designer, Layers</p>
                            <p className="text-base font-medium leading-6 max-md:max-w-full">Web Development Agency</p>
                        </div>
                        <div className="flex gap-5 justify-between">
                            <button className="flex justify-center items-center p-4 rounded-3xl border border-solid border-white border-opacity-50" aria-label="Previous testimonial">
                                <img loading="lazy" src="https://cdn.builder.io/api/v1/image/assets/TEMP/1ff5f97beb29c92c8ef08d84174660992937532ed2f66df263d8e6eb3f7206d5?apiKey=99f610f079bc4250a85747146003507a&&apiKey=99f610f079bc4250a85747146003507a" alt="" className="w-6 aspect-square" />
                            </button>
                            <button className="flex justify-center items-center p-4 rounded-3xl border border-solid border-white border-opacity-50" aria-label="Next testimonial">
                                <img loading="lazy" src="https://cdn.builder.io/api/v1/image/assets/TEMP/cc969320eb822628d51d559110ceeb7987aea8e5877e5db88226d2208ef42301?apiKey=99f610f079bc4250a85747146003507a&&apiKey=99f610f079bc4250a85747146003507a" alt="" className="w-6 aspect-square" />
                            </button>
                        </div>
                    </div> */}
                </div>
            </div>
        </aside>
    );
}

export default Testimonial;