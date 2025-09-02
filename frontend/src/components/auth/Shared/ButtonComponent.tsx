import { Button, Skeleton } from "antd";

const ButtonComponent = (props: any) => {
    const { onClick, type, htmlType, children, width, isLoading, height } = props;
    return (
        isLoading ? (
            <Skeleton.Button
                active
                shape="default"
                style={{ width: "360px", height: height ? `${height}` : "100%"}}
                className="font-[500] py-4 h-[42px] rounded-lg"
            />
        ) : (
            <Button
                type={type}
                onClick={onClick}
                htmlType={htmlType}
                style={{ width: width ? `${width}` : "100%", height: height ? `${height}` : "100%"}}
                className="font-[500] py-2 text-[16px] rounded-lg"
            >
                {children}
            </Button>
        )
    );
};

export default ButtonComponent;

