<template>
  <div class="relative flex flex-col h-full flex-1 min-w-0 px-5 ops-slide-up">
    <div
      class="ops-panel sm:min-w-[390px] flex flex-row items-center justify-between mt-3 mb-2 px-3 py-2 gap-1 sticky top-2 z-20 bg-[var(--background-white-main)] rounded-xl flex-shrink-0 border border-[var(--border-main)]">
      <div class="flex items-center flex-1">
        <div class="relative flex items-center">
          <div v-if="!isLeftPanelShow" @click="toggleLeftPanel"
            class="flex h-7 w-7 items-center justify-center cursor-pointer rounded-md hover:bg-[var(--fill-tsp-gray-main)]">
            <PanelLeft class="size-5 text-[var(--icon-secondary)]" />
          </div>
        </div>
      </div>
      <div class="max-w-full sm:max-w-[920px] sm:min-w-[390px] flex w-full items-center justify-between gap-2 overflow-hidden">
        <div class="min-w-0">
          <div class="text-[var(--text-primary)] text-lg font-semibold truncate">{{ currentNode?.name || '节点工作台' }}</div>
          <div class="text-xs text-[var(--text-tertiary)] truncate">
            {{ currentNode?.description || '选择节点后可查看健康状态、插件和日志' }}
          </div>
        </div>
        <button @click="refreshAll"
          class="h-8 px-3 rounded-full border border-[var(--border-main)] text-sm hover:bg-[var(--fill-tsp-white-main)]">
          刷新
        </button>
      </div>
      <div class="flex-1"></div>
    </div>

    <div class="mx-auto w-full max-w-full sm:max-w-[920px] sm:min-w-[390px] flex flex-col flex-1 min-h-0 pb-5">
      <div v-if="!currentNode" class="flex flex-1 items-center justify-center text-[var(--text-tertiary)]">
        还没有节点，请先在左侧节点菜单创建或选择一个节点。
      </div>
      <template v-else>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <div class="md:col-span-2 rounded-2xl border border-[var(--border-main)] bg-[var(--background-menu-white)] p-4">
            <div class="flex items-center justify-between mb-2">
              <div class="text-sm font-semibold">节点总体状态</div>
              <div class="text-xs px-2 py-0.5 rounded-full" :class="overviewPillClass">
                {{ overviewStatusText }}
              </div>
            </div>
            <div class="text-sm text-[var(--text-secondary)]">{{ overview?.summary || '正在拉取节点状态...' }}</div>
            <div class="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div class="rounded-lg bg-[var(--background-gray-main)]/60 px-2 py-2"><span class="text-[var(--text-tertiary)]">主机</span><div class="font-medium mt-1 truncate">{{ overview?.hostname || '-' }}</div></div>
              <div class="rounded-lg bg-[var(--background-gray-main)]/60 px-2 py-2"><span class="text-[var(--text-tertiary)]">系统</span><div class="font-medium mt-1 truncate">{{ overview?.os_name || '-' }}</div></div>
              <div class="rounded-lg bg-[var(--background-gray-main)]/60 px-2 py-2"><span class="text-[var(--text-tertiary)]">内核</span><div class="font-medium mt-1 truncate">{{ overview?.kernel || '-' }}</div></div>
              <div class="rounded-lg bg-[var(--background-gray-main)]/60 px-2 py-2"><span class="text-[var(--text-tertiary)]">在线时长</span><div class="font-medium mt-1 truncate">{{ overview?.uptime || '-' }}</div></div>
            </div>
          </div>
          <div class="rounded-2xl border border-[var(--border-main)] bg-[var(--background-menu-white)] p-4">
            <div class="text-sm font-semibold mb-2">关键指标</div>
            <div class="space-y-2">
              <div v-for="metric in overview?.metrics || []" :key="metric.label"
                class="rounded-lg border px-2 py-2" :class="metricClass(metric.level)">
                <div class="text-xs text-[var(--text-tertiary)]">{{ metric.label }}</div>
                <div class="text-sm font-semibold">{{ metric.value }}</div>
                <div v-if="metric.hint" class="text-[11px] text-[var(--text-tertiary)] mt-0.5">{{ metric.hint }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="rounded-2xl border border-[var(--border-main)] bg-[var(--background-menu-white)] flex flex-col flex-1 min-h-0">
          <div class="px-3 pt-3 pb-2 border-b border-[var(--border-main)] flex items-center gap-2">
            <button v-for="tab in tabs" :key="tab.key" @click="activeTab = tab.key"
              class="px-3 py-1.5 text-sm rounded-full border"
              :class="activeTab === tab.key ? 'bg-[var(--fill-tsp-primary)] border-[var(--border-btn-main)] text-[var(--text-primary)]' : 'border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--fill-tsp-gray-main)]'">
              {{ tab.label }}
            </button>
          </div>

          <div class="p-3 overflow-auto flex-1 min-h-0">
            <div v-if="activeTab === 'plugins'" class="space-y-3">
              <div class="rounded-xl border border-[var(--border-main)] p-3">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-sm font-semibold">SSH 插件</div>
                    <div class="text-xs text-[var(--text-tertiary)]">用于远程命令执行、监控采集和 AI 运维动作落地。</div>
                  </div>
                  <label class="flex items-center gap-2 text-sm">
                    <input type="checkbox" v-model="pluginForm.ssh_enabled" />
                    启用
                  </label>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3">
                  <input v-model="pluginForm.ssh_host" class="border rounded-lg px-2 py-1.5 text-sm" placeholder="IP / Host" />
                  <input v-model.number="pluginForm.ssh_port" type="number" class="border rounded-lg px-2 py-1.5 text-sm" placeholder="Port" />
                  <input v-model="pluginForm.ssh_username" class="border rounded-lg px-2 py-1.5 text-sm" placeholder="Username" />
                  <select v-model="pluginForm.ssh_auth_type" class="border rounded-lg px-2 py-1.5 text-sm">
                    <option value="password">password</option>
                    <option value="private_key">private_key</option>
                  </select>
                </div>
                <label class="mt-3 flex items-center gap-2 text-sm">
                  <input type="checkbox" v-model="pluginForm.ssh_require_approval" />
                  AI 指令需要审批
                </label>
                <div class="mt-3 flex justify-end">
                  <button @click="savePlugin"
                    class="px-3 py-1.5 rounded-lg border border-[var(--border-main)] bg-[var(--Button-primary-black)] text-[var(--text-onblack)] text-sm">
                    保存 SSH 插件配置
                  </button>
                </div>
              </div>
            </div>

            <div v-else-if="activeTab === 'logs'" class="space-y-2">
              <div v-for="log in logs" :key="log.log_id" class="rounded-xl border border-[var(--border-main)] p-2">
                <div class="flex items-center justify-between text-xs text-[var(--text-tertiary)]">
                  <span>{{ log.source }} · {{ log.actor_type }}</span>
                  <span>{{ formatTime(log.created_at) }}</span>
                </div>
                <pre class="text-xs mt-1 whitespace-pre-wrap bg-[var(--background-gray-main)]/60 p-2 rounded">{{ log.command }}</pre>
                <pre class="text-xs mt-1 whitespace-pre-wrap bg-[var(--background-gray-main)]/60 p-2 rounded">{{ log.output }}</pre>
              </div>
              <div v-if="logs.length === 0" class="text-sm text-[var(--text-tertiary)]">暂无日志</div>
            </div>

            <div v-else class="rounded-xl border border-dashed border-[var(--border-main)] p-6 text-sm text-[var(--text-tertiary)]">
              节点孪生系统区域预留。后续可接入拓扑、配置镜像和故障演练能力。
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { PanelLeft } from 'lucide-vue-next';
import { useLeftPanel } from '@/composables/useLeftPanel';
import { useOpsMenu } from '@/composables/useOpsMenu';
import {
  getNodeOverview,
  listNodeLogs,
  listServerNodes,
  updateServerNode,
  type NodeOverviewResponse,
  type SSHLogItem,
  type ServerNode,
} from '@/api/node';
import { showErrorToast, showSuccessToast } from '@/utils/toast';

type NodeBottomTab = 'plugins' | 'logs' | 'twin';

const route = useRoute();
const router = useRouter();
const { isLeftPanelShow, toggleLeftPanel } = useLeftPanel();
const { setActiveTab } = useOpsMenu();

const nodes = ref<ServerNode[]>([]);
const overview = ref<NodeOverviewResponse | null>(null);
const logs = ref<SSHLogItem[]>([]);
const activeTab = ref<NodeBottomTab>('plugins');

const pluginForm = reactive({
  ssh_enabled: false,
  ssh_host: '',
  ssh_port: 22,
  ssh_username: '',
  ssh_auth_type: 'password' as 'password' | 'private_key',
  ssh_require_approval: false,
});

const tabs = [
  { key: 'plugins' as NodeBottomTab, label: '插件' },
  { key: 'logs' as NodeBottomTab, label: '日志' },
  { key: 'twin' as NodeBottomTab, label: '孪生系统' },
];

const nodeId = computed(() => String(route.params.nodeId || ''));
const currentNode = computed(() => nodes.value.find((item) => item.node_id === nodeId.value) || null);

const overviewPillClass = computed(() => {
  const status = overview.value?.status;
  if (status === 'healthy') return 'bg-emerald-100 text-emerald-700';
  if (status === 'warning') return 'bg-amber-100 text-amber-700';
  return 'bg-rose-100 text-rose-700';
});

const overviewStatusText = computed(() => {
  const status = overview.value?.status;
  if (status === 'healthy') return '健康';
  if (status === 'warning') return '告警';
  return '风险';
});

const metricClass = (level: 'ok' | 'warn' | 'critical') => {
  if (level === 'ok') return 'border-emerald-200 bg-emerald-50/40';
  if (level === 'warn') return 'border-amber-200 bg-amber-50/40';
  return 'border-rose-200 bg-rose-50/40';
};

const formatTime = (value: string) => new Date(value).toLocaleString();

const syncPluginForm = (node: ServerNode | null) => {
  if (!node) return;
  pluginForm.ssh_enabled = node.ssh_enabled;
  pluginForm.ssh_host = node.ssh_host || '';
  pluginForm.ssh_port = node.ssh_port || 22;
  pluginForm.ssh_username = node.ssh_username || '';
  pluginForm.ssh_auth_type = node.ssh_auth_type;
  pluginForm.ssh_require_approval = node.ssh_require_approval;
};

const loadNodes = async () => {
  nodes.value = await listServerNodes();
  if (!nodeId.value && nodes.value.length > 0) {
    router.replace(`/chat/nodes/${nodes.value[0].node_id}`);
  }
};

const loadOverview = async () => {
  if (!nodeId.value) return;
  overview.value = await getNodeOverview(nodeId.value);
};

const loadLogs = async () => {
  if (!nodeId.value) return;
  logs.value = await listNodeLogs(nodeId.value, 100);
};

const refreshAll = async () => {
  if (!nodeId.value) return;
  try {
    await Promise.all([loadOverview(), loadLogs()]);
  } catch (error) {
    console.error(error);
    showErrorToast('节点状态刷新失败');
  }
};

const savePlugin = async () => {
  if (!currentNode.value) return;
  try {
    const node = currentNode.value;
    const payload = {
      name: node.name,
      description: node.description || '',
      remarks: node.remarks || '',
      ssh_enabled: pluginForm.ssh_enabled,
      ssh_host: pluginForm.ssh_host,
      ssh_port: pluginForm.ssh_port,
      ssh_username: pluginForm.ssh_username,
      ssh_auth_type: pluginForm.ssh_auth_type,
      ssh_password: node.ssh_password || '',
      ssh_private_key: node.ssh_private_key || '',
      ssh_passphrase: node.ssh_passphrase || '',
      ssh_require_approval: pluginForm.ssh_require_approval,
    };
    await updateServerNode(node.node_id, payload as any);
    showSuccessToast('SSH 插件配置已保存');
    await loadNodes();
    syncPluginForm(currentNode.value);
  } catch (error) {
    console.error(error);
    showErrorToast('保存失败，请检查配置');
  }
};

watch(currentNode, (node) => {
  syncPluginForm(node);
}, { immediate: true });

watch(nodeId, async () => {
  if (!nodeId.value) return;
  await refreshAll();
}, { immediate: true });

onMounted(async () => {
  setActiveTab('node');
  await loadNodes();
  await refreshAll();
});
</script>
