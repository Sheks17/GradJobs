import { Header } from "@/components/header";
import { ProviderCapabilities } from "@/components/provider-capabilities";

export default function ProvidersPage() {
  return (
    <>
      <Header active="sources" />
      <ProviderCapabilities />
    </>
  );
}
