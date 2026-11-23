import bharathiLogo from "../../assets/bharathi-logo.png";

export default function AuthBrand({ srTitle = "Bharathi Enterprises ERP" }) {
  return (
    <div className="w-full text-center">
      <h1 className="sr-only">{srTitle}</h1>
      <img
        src={bharathiLogo}
        alt="Bharathi Enterprises"
        width={640}
        height={235}
        className="mx-auto mb-6 h-14 w-auto max-w-full object-contain sm:h-16 md:h-20"
        decoding="async"
      />
      <p className="text-xs sm:text-sm text-gray-600">
        Electrical line materials, supply, and enterprise operations
      </p>
    </div>
  );
}