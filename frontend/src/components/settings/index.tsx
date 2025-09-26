import { Typography } from 'antd';

import ContentSection from './ContentSection';

const { Title } = Typography;

const Settings = () => (
  <>
    <Title className="mb-4" level={4}>
      Settings
    </Title>
    {/* <PageHeader title="Settings" /> */}
    <ContentSection />
  </>
);

export default Settings;
