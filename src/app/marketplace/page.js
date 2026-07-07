import dynamic from "next/dynamic";
import WorkspacePageLoading from "@/components/WorkspacePageLoading";

const MarketplaceClient = dynamic(() => import("./MarketplaceClient"), {
  loading: () => <WorkspacePageLoading />,
});

export default function MarketplacePage() {
  return <MarketplaceClient />;
}
