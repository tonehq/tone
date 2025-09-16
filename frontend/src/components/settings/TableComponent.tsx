import { useState } from 'react';

import { Avatar, Dropdown, Input, MenuProps, Select, Space, Table, Tabs, Tag, message } from 'antd';
import { MoreHorizontal, Search, UserPlus } from 'lucide-react';

import ModalComponent from '@/components/settings/ModalComponent';
import ButtonComponent from '@/components/Shared/UI Components/ButtonComponent';

const { Option } = Select;

interface MemberData {
  key: string;
  name: string;
  email: string;
  joinedDate: string;
  role: string;
  avatar: string | null;
}

interface InvitationData {
  key: string;
  name: string;
  email: string;
  invitedDate: string;
  status: string;
  role: string;
}

const MembersTable = () => {
  const [activeTab, setActiveTab] = useState('members');
  const [searchText, setSearchText] = useState('');
  const [sortBy, setSortBy] = useState('joined');
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const handleInviteUser = async (values: { name: string; email: string; role: string }) => {
    setLoading(true);
    try {
      // Replace with your API call
      console.log('Inviting user:', values);

      // Example:
      // await fetch("/api/invite", {
      //   method: "POST",
      //   headers: { "Content-Type": "application/json" },
      //   body: JSON.stringify(values),
      // });

      message.success(`Invitation sent to ${values.email}`);
      setInviteModalOpen(false);
    } catch (error) {
      message.error('Failed to send invitation');
    } finally {
      setLoading(false);
    }
  };

  // Sample members data
  const membersData: MemberData[] = [
    {
      key: '1',
      name: 'skarastro@gmail.com',
      email: 'skarastro@gmail.com',
      joinedDate: 'September 2, 2025',
      role: 'Member',
      avatar: null,
    },
    {
      key: '2',
      name: 'Karthikeyan S',
      email: 'karthik@productfusion.co',
      joinedDate: 'March 12, 2025',
      role: 'Admin',
      avatar: null,
    },
  ];

  // Sample invitations data
  const invitationsData: InvitationData[] = [
    {
      key: '1',
      name: 'john@example.com',
      email: 'john@example.com',
      invitedDate: 'September 1, 2025',
      status: 'Pending',
      role: 'Member',
    },
    {
      key: '2',
      name: 'sarah@company.com',
      email: 'sarah@company.com',
      invitedDate: 'August 30, 2025',
      status: 'Sent',
      role: 'Member',
    },
  ];

  const getInitials = (name: string): string => {
    if (name.includes('@')) {
      return name.charAt(0).toUpperCase();
    }
    return name
      .split(' ')
      .map((n: string) => n[0])
      .join('')
      .toUpperCase();
  };
  const items: MenuProps['items'] = [
    {
      key: 'edit',
      label: 'Edit Role',
    },
    {
      key: 'remove',
      label: 'Remove User',
      danger: true,
    },
  ];

  const memberColumns = [
    {
      title: 'User',
      dataIndex: 'name',
      key: 'user',
      render: (text: string, record: MemberData) => (
        <Space>
          <Avatar
            size={40}
            style={{
              backgroundColor: '#7c3aed',
              fontSize: '16px',
              fontWeight: 'bold',
            }}
          >
            {getInitials(text)}
          </Avatar>
          <div>
            <div style={{ fontWeight: 500 }}>{record.name}</div>
            {record.email !== record.name && (
              <div style={{ color: '#666', fontSize: '12px' }}>{record.email}</div>
            )}
          </div>
        </Space>
      ),
    },
    {
      title: 'Joined',
      dataIndex: 'joinedDate',
      key: 'joined',
      sorter: true,
    },
    {
      title: 'Role',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => (
        <Select value={role} style={{ width: 120 }} variant="borderless" suffixIcon={null}>
          <Option value="Admin">Admin</Option>
          <Option value="Member">Member</Option>
        </Select>
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 50,
      render: (_: any, record: MemberData) => (
        <Dropdown
          menu={{
            items,
            style: { width: 130 },
          }}
          trigger={['click']}
          getPopupContainer={(triggerNode) => triggerNode?.parentElement || document.body}
        >
          <span>
            <ButtonComponent type="text" icon={<MoreHorizontal size={16} />} />
          </span>
        </Dropdown>
      ),
    },
  ];

  const invitationColumns = [
    {
      title: 'User',
      dataIndex: 'name',
      key: 'user',
      render: (text: string, record: InvitationData) => (
        <Space>
          <Avatar
            size={40}
            style={{
              backgroundColor: '#7c3aed',
              fontSize: '16px',
              fontWeight: 'bold',
            }}
          >
            {getInitials(text)}
          </Avatar>
          <div>
            <div style={{ fontWeight: 500 }}>{record.email}</div>
          </div>
        </Space>
      ),
    },
    {
      title: 'Invited',
      dataIndex: 'invitedDate',
      key: 'invited',
      sorter: true,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'Pending' ? 'orange' : 'blue'}>{status}</Tag>
      ),
    },
    {
      title: 'Role',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => (
        <Select value={role} style={{ width: 120 }} variant="borderless" suffixIcon={null}>
          <Option value="Admin">Admin</Option>
          <Option value="Member">Member</Option>
        </Select>
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 50,
      render: (_: any, record: InvitationData) => (
        <Dropdown
          menu={{
            items: [
              {
                key: 'resend',
                label: 'Resend Invitation',
              },
              {
                key: 'cancel',
                label: 'Cancel Invitation',
                danger: true,
              },
            ],
          }}
          trigger={['click']}
        >
          <ButtonComponent type="text" icon={<MoreHorizontal size={16} />} />
        </Dropdown>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'members',
      label: 'Members',
    },
    {
      key: 'invitations',
      label: 'Invitations',
    },
  ];

  return (
    <div style={{ padding: '24px', backgroundColor: '#f5f5f5', height: 'calc(100vh - 75px)' }}>
      <div style={{ backgroundColor: 'white', borderRadius: '8px', overflow: 'hidden' }}>
        {/* Tabs Navigation */}
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          style={{
            paddingLeft: '24px',
            marginBottom: 0,
          }}
          tabBarStyle={{
            borderBottom: '1px solid #f0f0f0',
            marginBottom: '24px',
          }}
        />

        {/* Table Content */}
        <div style={{ padding: '0 24px 24px' }}>
          {/* Header Controls */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
            }}
          >
            <Space>
              <Input
                placeholder="Search..."
                value={searchText}
                onChange={(e: any) => setSearchText(e.target.value)}
                style={{ width: 300 }}
                prefix={<Search size={16} color="#c1bfbf" style={{ marginRight: 8 }} />}
              />
            </Space>
            <ButtonComponent
              text="Invite user"
              type="primary"
              icon={<UserPlus size={16} />}
              onClick={() => setInviteModalOpen(true)}
              active={true}
            />
          </div>

          {/* Table */}
          {activeTab === 'members' ? (
            <Table
              columns={memberColumns}
              dataSource={membersData}
              pagination={false}
              showHeader={true}
              size="large"
              style={{
                backgroundColor: 'white',
              }}
            />
          ) : (
            <Table
              columns={invitationColumns}
              dataSource={invitationsData}
              pagination={false}
              showHeader={true}
              size="large"
              style={{
                backgroundColor: 'white',
              }}
            />
          )}
        </div>
      </div>
      <ModalComponent
        open={inviteModalOpen}
        onCancel={() => setInviteModalOpen(false)}
        onInvite={handleInviteUser}
        loading={loading}
      />
    </div>
  );
};

export default MembersTable;
