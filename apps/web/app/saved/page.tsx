import { Header } from "@/components/header";
import { SavedJobs } from "@/components/saved-jobs";
export default function SavedPage() {
  return (
    <>
      <Header active="saved" />
      <SavedJobs />
    </>
  );
}
