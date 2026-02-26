'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import axiosInstance from '@/utils/axios';
import { useEffect, useState } from 'react';
import ApiKeysTab from './ApiKeysTab';
import PublicKeysTab from './PublicKeysTab';

export default function Apikeys() {
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const fetchApiKeys = async () => {
      setIsLoading(true);
      try {
        const response = await axiosInstance.get('/generated-api-keys/list');
        console.log(response.data, 'response.data');
      } catch (error) {
        console.log(error, 'error');
      } finally {
        setIsLoading(false);
      }
    };
    fetchApiKeys();
  }, []);

  console.log(isLoading, 'isLoading');

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-foreground">API Keys</h2>
      </div>

      <Tabs defaultValue="api-keys">
        <TabsList variant="line">
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="public-keys">Public Keys</TabsTrigger>
        </TabsList>

        <TabsContent value="api-keys" className="pt-4">
          <ApiKeysTab />
        </TabsContent>

        <TabsContent value="public-keys" className="pt-4">
          <PublicKeysTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
