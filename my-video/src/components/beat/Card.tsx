import React, {CSSProperties, ReactNode} from "react";

type CardProps = {
  children: ReactNode;
  style?: CSSProperties;
};

export const Card: React.FC<CardProps> = ({children, style}) => {
  return (
    <div
      style={{
        borderRadius: 28,
        border: "1px solid rgba(255,255,255,0.18)",
        background:
          "linear-gradient(160deg, rgba(11,20,45,0.92), rgba(6,13,35,0.82))",
        boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
        padding: 34,
        color: "#f7f8ff",
        ...style,
      }}
    >
      {children}
    </div>
  );
};
