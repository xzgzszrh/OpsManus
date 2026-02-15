<template>
  <div class="w-full">
    <div class="flex items-center justify-between mb-3">
      <div class="text-sm font-medium text-[var(--text-primary)]">Server Nodes ({{ nodes.length }}/8)</div>
      <button
        class="h-8 px-3 rounded-md bg-[var(--Button-primary-black)] text-[var(--text-onblack)] text-sm disabled:opacity-40"
        :disabled="nodes.length >= 8"
        @click="startCreate"
      >Add Node</button>
    </div>

    <div class="space-y-2 max-h-[220px] overflow-auto pr-1">
      <div
        v-for="node in nodes"
        :key="node.node_id"
        class="border border-[var(--border-main)] rounded-lg p-3 bg-[var(--background-menu-white)]"
      >
        <div class="flex items-center justify-between gap-2">
          <div class="min-w-0">
            <div class="text-sm font-medium text-[var(--text-primary)] truncate">{{ node.name }}</div>
            <div class="text-xs text-[var(--text-tertiary)] truncate">
              {{ node.ssh_enabled ? `${node.ssh_username || 'user'}@${node.ssh_host || '-'}:${node.ssh_port}` : 'SSH disabled' }}
            </div>
          </div>
          <div class="flex gap-1">
            <button class="text-xs px-2 py-1 rounded border" @click="openMonitor(node)">Monitor</button>
            <button class="text-xs px-2 py-1 rounded border" @click="openLogs(node)">Logs</button>
            <button class="text-xs px-2 py-1 rounded border" @click="startEdit(node)">Edit</button>
            <button class="text-xs px-2 py-1 rounded border text-red-600" @click="remove(node)">Delete</button>
          </div>
        </div>
      </div>
      <div v-if="!nodes.length" class="text-xs text-[var(--text-tertiary)]">No nodes configured yet.</div>
    </div>

    <div v-if="editing" class="mt-4 border border-[var(--border-main)] rounded-lg p-3 space-y-3">
      <div class="text-sm font-medium">{{ form.node_id ? 'Edit Node' : 'Create Node' }}</div>

      <input v-model="form.name" class="w-full border rounded px-2 py-1 text-sm" placeholder="Node name" />
      <textarea v-model="form.description" class="w-full border rounded px-2 py-1 text-sm" rows="2" placeholder="Description"></textarea>
      <textarea v-model="form.remarks" class="w-full border rounded px-2 py-1 text-sm" rows="2" placeholder="Remarks"></textarea>

      <label class="flex items-center gap-2 text-sm">
        <input type="checkbox" v-model="form.ssh_enabled" /> Enable SSH
      </label>

      <div v-if="form.ssh_enabled" class="grid grid-cols-2 gap-2">
        <input v-model="form.ssh_host" class="border rounded px-2 py-1 text-sm col-span-2" placeholder="Host / IP" />
        <input v-model.number="form.ssh_port" type="number" class="border rounded px-2 py-1 text-sm" placeholder="Port" />
        <input v-model="form.ssh_username" class="border rounded px-2 py-1 text-sm" placeholder="Username" />

        <select v-model="form.ssh_auth_type" class="border rounded px-2 py-1 text-sm col-span-2">
          <option value="password">Password</option>
          <option value="private_key">Private Key</option>
        </select>

        <input v-if="form.ssh_auth_type === 'password'" v-model="form.ssh_password" type="password" class="border rounded px-2 py-1 text-sm col-span-2" placeholder="Password" />

        <textarea v-if="form.ssh_auth_type === 'private_key'" v-model="form.ssh_private_key" class="border rounded px-2 py-1 text-sm col-span-2" rows="4" placeholder="Private key"></textarea>
        <input v-if="form.ssh_auth_type === 'private_key'" v-model="form.ssh_passphrase" type="password" class="border rounded px-2 py-1 text-sm col-span-2" placeholder="Passphrase (optional)" />

        <label class="flex items-center gap-2 text-sm col-span-2">
          <input type="checkbox" v-model="form.ssh_require_approval" /> AI command requires approval
        </label>
      </div>

      <div class="flex justify-end gap-2">
        <button class="px-3 py-1 text-sm border rounded" @click="cancelEdit">Cancel</button>
        <button class="px-3 py-1 text-sm border rounded bg-[var(--Button-primary-black)] text-[var(--text-onblack)]" @click="save">Save</button>
      </div>
    </div>

    <div v-if="monitorNodeItem" class="mt-4 border border-[var(--border-main)] rounded-lg p-3">
      <div class="flex justify-between mb-2">
        <div class="text-sm font-medium">{{ monitorNodeItem.name }} Monitor</div>
        <button class="text-xs border rounded px-2" @click="refreshMonitor">Refresh</button>
      </div>
      <pre class="text-xs whitespace-pre-wrap bg-[var(--background-gray-main)] p-2 rounded max-h-[200px] overflow-auto">{{ monitorText }}</pre>
    </div>

    <div v-if="logNodeItem" class="mt-4 border border-[var(--border-main)] rounded-lg p-3">
      <div class="flex justify-between mb-2">
        <div class="text-sm font-medium">{{ logNodeItem.name }} Logs</div>
        <button class="text-xs border rounded px-2" @click="refreshLogs">Refresh</button>
      </div>
      <div class="space-y-2 max-h-[200px] overflow-auto">
        <div v-for="log in logs" :key="log.log_id" class="p-2 rounded bg-[var(--background-gray-main)]">
          <div class="text-[11px] text-[var(--text-tertiary)]">{{ log.created_at }} | {{ log.source }} | {{ log.success ? 'ok' : 'failed' }}</div>
          <div class="text-xs font-mono">$ {{ log.command }}</div>
          <pre class="text-xs whitespace-pre-wrap">{{ log.output }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import {
  createServerNode,
  deleteServerNode,
  listNodeLogs,
  listServerNodes,
  monitorNode,
  updateServerNode,
  type ServerNode,
  type SSHLogItem,
} from '@/api/node';
import { showErrorToast, showSuccessToast } from '@/utils/toast';

const nodes = ref<ServerNode[]>([]);
const logs = ref<SSHLogItem[]>([]);
const monitorText = ref('');
const editing = ref(false);
const monitorNodeItem = ref<ServerNode | null>(null);
const logNodeItem = ref<ServerNode | null>(null);

const form = reactive<Omit<ServerNode, 'created_at' | 'updated_at'>>({
  node_id: '',
  name: '',
  description: '',
  remarks: '',
  ssh_enabled: false,
  ssh_host: '',
  ssh_port: 22,
  ssh_username: '',
  ssh_auth_type: 'password',
  ssh_password: '',
  ssh_private_key: '',
  ssh_passphrase: '',
  ssh_require_approval: false,
});

const resetForm = () => {
  Object.assign(form, {
    node_id: '',
    name: '',
    description: '',
    remarks: '',
    ssh_enabled: false,
    ssh_host: '',
    ssh_port: 22,
    ssh_username: '',
    ssh_auth_type: 'password',
    ssh_password: '',
    ssh_private_key: '',
    ssh_passphrase: '',
    ssh_require_approval: false,
  });
};

const loadNodes = async () => {
  try {
    nodes.value = await listServerNodes();
  } catch (e: any) {
    showErrorToast(e?.response?.data?.msg || 'Failed to load nodes');
  }
};

const startCreate = () => {
  resetForm();
  editing.value = true;
};

const startEdit = (node: ServerNode) => {
  Object.assign(form, node);
  editing.value = true;
};

const cancelEdit = () => {
  editing.value = false;
  resetForm();
};

const save = async () => {
  if (!form.name.trim()) {
    showErrorToast('Node name is required');
    return;
  }
  try {
    const payload = {
      name: form.name,
      description: form.description,
      remarks: form.remarks,
      ssh_enabled: form.ssh_enabled,
      ssh_host: form.ssh_host,
      ssh_port: form.ssh_port,
      ssh_username: form.ssh_username,
      ssh_auth_type: form.ssh_auth_type,
      ssh_password: form.ssh_password,
      ssh_private_key: form.ssh_private_key,
      ssh_passphrase: form.ssh_passphrase,
      ssh_require_approval: form.ssh_require_approval,
    };

    if (form.node_id) {
      await updateServerNode(form.node_id, payload as any);
      showSuccessToast('Node updated');
    } else {
      await createServerNode(payload as any);
      showSuccessToast('Node created');
    }
    editing.value = false;
    await loadNodes();
  } catch (e: any) {
    showErrorToast(e?.response?.data?.msg || 'Save failed');
  }
};

const remove = async (node: ServerNode) => {
  try {
    await deleteServerNode(node.node_id);
    showSuccessToast('Node deleted');
    await loadNodes();
  } catch (e: any) {
    showErrorToast(e?.response?.data?.msg || 'Delete failed');
  }
};

const openMonitor = async (node: ServerNode) => {
  monitorNodeItem.value = node;
  await refreshMonitor();
};

const refreshMonitor = async () => {
  if (!monitorNodeItem.value) return;
  try {
    const data = await monitorNode(monitorNodeItem.value.node_id);
    monitorText.value = data.system_info;
  } catch (e: any) {
    showErrorToast(e?.response?.data?.msg || 'Monitor failed');
  }
};

const openLogs = async (node: ServerNode) => {
  logNodeItem.value = node;
  await refreshLogs();
};

const refreshLogs = async () => {
  if (!logNodeItem.value) return;
  try {
    logs.value = await listNodeLogs(logNodeItem.value.node_id);
  } catch (e: any) {
    showErrorToast(e?.response?.data?.msg || 'Load logs failed');
  }
};

onMounted(loadNodes);
</script>
