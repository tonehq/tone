"use client";

const Container = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="flex w-screen h-screen overflow-hidden">
      {/* Left side */}
      <div className="w-1/2 h-full flex items-center justify-center">
        <div className="w-full h-full flex items-center justify-center rounded-lg shadow-md">
          {children}
        </div>
      </div>

      {/* Right side */}
      <div className="w-1/2 h-full">
        <img
          src="https://cdn.builder.io/api/v1/image/assets/TEMP/064d49d468d0952bd0a54eff0df8fb9a191373a750f515c5d402d20433ce4293?apiKey=99f610f079bc4250a85747146003507a&&apiKey=99f610f079bc4250a85747146003507a"
          alt="app logo"
          className="w-full h-full object-cover"
        />
      </div>
    </div>
  );
};

export default Container;
