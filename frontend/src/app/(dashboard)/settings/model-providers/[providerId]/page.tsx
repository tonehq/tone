import ServiceProviderDetailPage from '@/components/service-providers/ServiceProviderDetailPage';

// Provider-scoped detail page (no service_type in the URL). Reached from the
// "Not connected" cards on the listing so the user can add API keys and
// browse/edit models for a provider they haven't set up yet. The detail
// component treats a missing service_type as "show all kinds", so keys +
// models render across llm/stt/tts. Landing on
// /model-providers/{providerId}/{serviceType} still works (that path is
// used from connected cards) and narrows to a single kind.
const Page = () => (
  <div className="flex min-h-0 flex-1 flex-col p-6 lg:p-8">
    <ServiceProviderDetailPage />
  </div>
);

export default Page;
