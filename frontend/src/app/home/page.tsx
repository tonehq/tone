"use client";
import { useRouter } from "next/navigation";
import ButtonComponent from "@/components/Shared/UI Components/ButtonComponent";

const HomePage = () => {
  const router = useRouter();
  return (
    <div style={{ padding: "24px", width: "200px" }} >
      <h1>Home</h1>
      <ButtonComponent
        text="Go to settings"
        onClick={() => router.push("/settings")}
        active={true}
      />
    </div>
  );
};

export default HomePage;