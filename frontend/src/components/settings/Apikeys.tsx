'use client';

import ApiKeysTab from './ApiKeysTab';

export default function Apikeys() {
  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-foreground">API Keys</h2>
      </div>
      <ApiKeysTab />
    </div>
  );
}
