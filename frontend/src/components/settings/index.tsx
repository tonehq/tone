import { Typography } from 'antd';

import MembersTable from './TableComponent';

const { Title } = Typography;

const Settings = () => (
  <div>
    <Title className="mb-4" level={4}>
      Settings
    </Title>
    <MembersTable />
  </div>
);

export default Settings;
