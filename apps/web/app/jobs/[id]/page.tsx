import { Header } from "@/components/header";
import { JobDetail } from "@/components/job-detail";
export default async function JobPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <>
      <Header />
      <JobDetail id={id} />
    </>
  );
}
