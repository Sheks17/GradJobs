import { Header } from "@/components/header";
import { Ingestion } from "@/components/ingestion";

export default function IngestionPage() {
  return (
    <>
      <Header active="sources" />
      <Ingestion />
    </>
  );
}
