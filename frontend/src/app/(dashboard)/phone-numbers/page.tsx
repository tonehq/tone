'use client';

import CustomButton from '@/components/shared/CustomButton';
import { Plus } from 'lucide-react';

export default function PhoneNumbersPage() {
  return (
    <div className="flex-1 rounded-[5px] p-2" style={{ height: 'calc(100vh - 16px)' }}>
      <div className="h-full overflow-hidden rounded-[5px] border bg-white p-3">
        <div className="mb-2 flex items-center justify-between">
          <h5 className="text-lg font-semibold">Phone Numbers</h5>
          <CustomButton type="primary" icon={<Plus className="size-4" />}>
            Link a Phone Number to An Agent
          </CustomButton>
        </div>
      </div>
    </div>
  );
}
