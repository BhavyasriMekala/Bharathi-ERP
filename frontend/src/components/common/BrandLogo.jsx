import bharathiLogoUrl from "../../assets/bharathi-enterprises-logo.png";

const LOGO_SRC = bharathiLogoUrl;

const SIZE_CLASS = {
  sm: "h-9 w-auto max-w-[9.5rem]",
  md: "h-12 w-auto max-w-[11rem]",
  lg: "h-14 w-auto max-w-[13rem]",
  xl: "h-14 w-auto max-w-[14rem] sm:max-w-[16rem]",
  hero: "h-24 w-auto max-w-[18rem] sm:max-w-[20rem]",
};

const LOGIN_WORDMARK_CLASS =
  "h-[5rem] w-auto max-w-full sm:h-[5.75rem] md:h-[6.5rem]";

export default function BrandLogo({
  size = "md",
  variant = "default",
  className = "",
  imageClassName = "",
  showName = false,
  name = "Bharathi Enterprises",
  nameClassName = "",
  nameStyle,
}) {
  const sizeClass =
    variant === "login" ? LOGIN_WORDMARK_CLASS : SIZE_CLASS[size] || SIZE_CLASS.md;

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <img
        src={LOGO_SRC}
        alt="Bharathi Enterprises logo"
        className={`${sizeClass} object-contain object-center shrink-0 ${imageClassName}`}
        decoding="async"
        fetchpriority={variant === "login" ? "high" : "auto"}
      />
      {showName ? (
        <span className={nameClassName} style={nameStyle}>
          {name}
        </span>
      ) : null}
    </div>
  );
}