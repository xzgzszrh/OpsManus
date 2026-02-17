<template>
  <div class="relative flex flex-col h-full flex-1 min-w-0 px-5 pt-3 pb-5 ops-slide-up node-page">
    <div class="w-full max-w-none flex flex-col flex-1 min-h-0">
      <div class="node-topbar rounded-2xl border px-4 py-3 mb-3">
        <div class="flex items-center gap-3">
          <div v-if="!isLeftPanelShow" @click="toggleLeftPanel"
            class="flex h-8 w-8 items-center justify-center cursor-pointer rounded-md hover:bg-[var(--fill-tsp-gray-main)] transition">
            <PanelLeft class="size-5 text-[var(--icon-secondary)]" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Node Dashboard</div>
            <div class="text-xl font-semibold text-[var(--text-primary)] truncate leading-tight">{{ currentNode?.name || '节点工作台' }}</div>
            <div class="text-xs text-[var(--text-tertiary)] truncate mt-0.5">{{ currentNode?.description || '选择节点后可查看健康状态、插件和日志' }}</div>
          </div>
          <button @click="refreshAll" class="node-refresh-btn">刷新状态</button>
        </div>
      </div>

      <div v-if="!currentNode" class="node-empty flex flex-1 items-center justify-center rounded-2xl border">
        还没有节点，请先在左侧节点菜单创建或选择一个节点。
      </div>

      <template v-else>
        <div class="grid grid-cols-1 gap-3 mb-3">
          <section class="node-card node-section rounded-2xl p-4">
            <div class="flex items-center justify-between gap-2 mb-3">
              <div class="text-sm font-semibold text-[var(--text-primary)]">节点综合状态</div>
              <span class="node-status-chip" :class="statusChipClass">{{ overviewStatusText }}</span>
            </div>
            <div class="text-sm text-[var(--text-secondary)] leading-6">{{ overview?.summary || '正在拉取节点状态...' }}</div>
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-2 mt-3 node-grid-sep">
              <div class="node-kv-cell">
                <div class="node-kv-cell__label">主机</div>
                <div class="node-kv-cell__value truncate">{{ overview?.hostname || '-' }}</div>
              </div>
              <div class="node-kv-cell">
                <div class="node-kv-cell__label">系统</div>
                <div class="node-kv-cell__value truncate">{{ overview?.os_name || '-' }}</div>
              </div>
              <div class="node-kv-cell">
                <div class="node-kv-cell__label">内核</div>
                <div class="node-kv-cell__value truncate">{{ overview?.kernel || '-' }}</div>
              </div>
              <div class="node-kv-cell">
                <div class="node-kv-cell__label">在线时长</div>
                <div class="node-kv-cell__value truncate">{{ overview?.uptime || '-' }}</div>
              </div>
            </div>
            <div class="mt-3 pt-3 border-t border-[var(--border-main)]">
              <div class="text-sm font-semibold text-[var(--text-primary)] mb-2">关键指标</div>
              <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-2 node-grid-sep">
                <article v-for="metric in overview?.metrics || []" :key="metric.label" class="metric-row" :class="metricRowClass(metric.level)">
                  <div class="flex items-center justify-between">
                    <div class="text-xs text-[var(--text-secondary)]">{{ metric.label }}</div>
                    <div class="text-base font-semibold text-[var(--text-primary)]">{{ metric.value }}</div>
                  </div>
                  <div class="metric-track mt-1.5">
                    <div class="metric-track__inner" :style="{ width: `${metricPercent(metric)}%` }"></div>
                  </div>
                  <div v-if="metric.hint" class="text-[11px] text-[var(--text-tertiary)] mt-1">{{ metric.hint }}</div>
                </article>
              </div>
            </div>
          </section>
        </div>

        <div class="grid grid-cols-1 gap-3 mb-3">
          <section class="node-card node-section rounded-2xl p-3">
            <div class="flex items-center justify-between mb-2">
              <div class="text-sm font-semibold text-[var(--text-primary)]">资源快照</div>
              <div class="text-xs text-[var(--text-tertiary)]">{{ overview?.checked_at ? formatTime(overview.checked_at) : '-' }}</div>
            </div>
            <div class="grid grid-cols-3 gap-2 node-grid-sep">
              <div class="trend-cell">
                <div class="trend-cell__label">CPU</div>
                <div class="trend-cell__value">{{ metricValue('CPU 负载') }}</div>
                <div class="trend-line"><span v-for="(v, index) in trendBars('CPU 负载')" :key="`cpu-${index}`" :style="{ height: `${v}%` }"></span></div>
              </div>
              <div class="trend-cell">
                <div class="trend-cell__label">内存</div>
                <div class="trend-cell__value">{{ metricValue('内存使用') }}</div>
                <div class="trend-line"><span v-for="(v, index) in trendBars('内存使用')" :key="`mem-${index}`" :style="{ height: `${v}%` }"></span></div>
              </div>
              <div class="trend-cell">
                <div class="trend-cell__label">磁盘</div>
                <div class="trend-cell__value">{{ metricValue('磁盘使用(/)') }}</div>
                <div class="trend-line"><span v-for="(v, index) in trendBars('磁盘使用(/)')" :key="`disk-${index}`" :style="{ height: `${v}%` }"></span></div>
              </div>
            </div>
          </section>
        </div>

        <section class="node-card node-card--solid rounded-2xl flex flex-col flex-1 min-h-0 overflow-hidden">
          <div class="px-3 py-2 border-b border-[var(--border-main)] bg-[var(--background-gray-main)]/50 flex items-center gap-2">
            <button v-for="tab in tabs" :key="tab.key" @click="activeTab = tab.key" class="tab-btn" :class="activeTab === tab.key ? 'tab-btn--active' : ''">
              {{ tab.label }}
            </button>
          </div>

          <div class="p-3 overflow-auto flex-1 min-h-0">
            <div v-if="activeTab === 'plugins'" class="grid grid-cols-1 lg:grid-cols-12 gap-3">
              <div class="lg:col-span-8 plugin-panel">
                <div class="flex items-center justify-between gap-2">
                  <div>
                    <div class="text-base font-semibold text-[var(--text-primary)]">SSH 插件</div>
                    <div class="text-xs text-[var(--text-tertiary)]">用于远程命令执行、监控采集和 AI 运维动作落地。</div>
                  </div>
                  <label class="inline-flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                    <input type="checkbox" v-model="pluginForm.ssh_enabled" />
                    启用
                  </label>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3">
                  <input v-model="pluginForm.ssh_host" class="node-input" placeholder="IP / Host" />
                  <input v-model.number="pluginForm.ssh_port" type="number" class="node-input" placeholder="Port" />
                  <input v-model="pluginForm.ssh_username" class="node-input" placeholder="Username" />
                  <select v-model="pluginForm.ssh_auth_type" class="node-input">
                    <option value="password">password</option>
                    <option value="private_key">private_key</option>
                  </select>
                </div>

                <div class="mt-3 flex items-center justify-between gap-2 flex-wrap">
                  <label class="inline-flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                    <input type="checkbox" v-model="pluginForm.ssh_require_approval" />
                    AI 指令需要审批
                  </label>
                  <button @click="savePlugin" class="node-save-btn">保存 SSH 配置</button>
                </div>
              </div>

              <div class="lg:col-span-4 plugin-panel plugin-hint">
                <div class="text-sm font-semibold text-[var(--text-primary)]">插件说明</div>
                <ul class="mt-2 text-xs text-[var(--text-tertiary)] space-y-1.5 leading-5">
                  <li>插件是节点能力模块，SSH 是第一类插件。</li>
                  <li>后续可扩展探针、MCP、部署流水线等插件。</li>
                  <li>审批开启后，AI 每条命令执行前都需要你确认。</li>
                </ul>
              </div>
            </div>

            <div v-else-if="activeTab === 'logs'" class="space-y-2">
              <div class="flex items-center justify-end">
                <label class="inline-flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
                  <input type="checkbox" v-model="includeSystemLogs" />
                  显示系统采集日志
                </label>
              </div>
              <article v-for="log in logs" :key="log.log_id" class="log-card">
                <div class="flex items-center justify-between text-xs text-[var(--text-tertiary)]">
                  <span>{{ log.source }} · {{ log.actor_type }}</span>
                  <span>{{ formatTime(log.created_at) }}</span>
                </div>
                <pre class="log-block mt-2">$ {{ log.command }}</pre>
                <pre class="log-block mt-2">{{ log.output }}</pre>
              </article>
              <div v-if="logs.length === 0" class="text-sm text-[var(--text-tertiary)]">暂无日志</div>
            </div>

            <div v-else class="twin-panel">
              <div class="text-sm text-[var(--text-primary)]">节点孪生系统（预留）</div>
              <div class="text-xs text-[var(--text-tertiary)] mt-1">后续接入拓扑视图、变更模拟、故障演练和配置镜像。</div>
            </div>
          </div>
        </section>
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
  type NodeOverviewMetric,
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
const includeSystemLogs = ref(false);

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

const overviewStatusText = computed(() => {
  const status = overview.value?.status;
  if (status === 'healthy') return '健康';
  if (status === 'warning') return '告警';
  return '风险';
});

const statusChipClass = computed(() => {
  const status = overview.value?.status;
  if (status === 'healthy') return 'node-status-chip--ok';
  if (status === 'warning') return 'node-status-chip--warn';
  return 'node-status-chip--critical';
});

const metricRowClass = (level: 'ok' | 'warn' | 'critical') => {
  if (level === 'ok') return 'metric-row--ok';
  if (level === 'warn') return 'metric-row--warn';
  return 'metric-row--critical';
};

const parsePercent = (value: string): number => {
  const match = value.match(/(\d+(?:\.\d+)?)%/);
  if (match) return Math.max(0, Math.min(100, Number(match[1])));
  const numeric = value.match(/(\d+(?:\.\d+)?)/);
  if (!numeric) return 35;
  return Math.max(12, Math.min(100, Number(numeric[1]) * 10));
};

const metricPercent = (metric: NodeOverviewMetric): number => parsePercent(metric.value || '');

const getMetric = (label: string): NodeOverviewMetric | undefined => {
  return overview.value?.metrics.find((item) => item.label === label);
};

const metricValue = (label: string): string => getMetric(label)?.value || '-';

const trendBars = (label: string): number[] => {
  const base = metricPercent(getMetric(label) || { label: '', value: '35', level: 'ok' });
  return [base * 0.62, base * 0.78, base * 0.56, base * 0.9, base * 0.68, base * 0.84, base * 0.72].map((v) => {
    return Math.max(14, Math.min(100, Math.round(v)));
  });
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
  logs.value = await listNodeLogs(nodeId.value, 100, includeSystemLogs.value);
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

watch(includeSystemLogs, () => {
  loadLogs();
});

onMounted(async () => {
  setActiveTab('node');
  await loadNodes();
  await refreshAll();
});
</script>

<style scoped>
.node-page {
  background: transparent;
}

.node-topbar,
.node-card,
.node-empty {
  border-color: transparent;
  background: transparent;
  box-shadow: none;
}

.node-topbar {
  border-radius: 0;
  border-bottom: 1px solid color-mix(in srgb, var(--border-main) 75%, transparent);
}

.node-section {
  position: relative;
}

.node-section::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  border-top: 1px solid color-mix(in srgb, var(--border-main) 78%, transparent);
}

.node-section::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  border-bottom: 1px solid color-mix(in srgb, var(--border-main) 62%, transparent);
}

.node-grid-sep > * {
  position: relative;
}

.node-grid-sep > *::after {
  content: "";
  position: absolute;
  top: 6px;
  bottom: 6px;
  right: -6px;
  width: 1px;
  background: color-mix(in srgb, var(--border-main) 55%, transparent);
  display: none;
}

.node-grid-sep > *:last-child::after {
  display: none;
}

.node-card--solid {
  background: var(--background-white-main);
  border-color: var(--border-main);
  box-shadow: 0 1px 2px var(--shadow-XS);
}

.node-refresh-btn {
  height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--border-main);
  background: var(--background-white-main);
  color: var(--text-secondary);
  font-size: 13px;
}

.node-refresh-btn:hover {
  background: var(--fill-tsp-white-main);
}

.node-status-chip {
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
}

.node-status-chip--ok {
  color: #116f44;
  background: #d9f4e6;
  border-color: #a9e6c8;
}

.node-status-chip--warn {
  color: #8a5a00;
  background: #fff1d7;
  border-color: #ffd489;
}

.node-status-chip--critical {
  color: #a12b3d;
  background: #ffe1e7;
  border-color: #ffb8c5;
}

.node-kv-cell {
  border-radius: 2px;
  border: 1px solid color-mix(in srgb, var(--border-main) 78%, transparent);
  background: color-mix(in srgb, var(--background-white-main) 12%, transparent);
  padding: 8px 10px;
}

.node-kv-cell__label {
  font-size: 11px;
  color: var(--text-tertiary);
}

.node-kv-cell__value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-top: 6px;
}

.metric-row {
  border: 1px solid color-mix(in srgb, var(--border-main) 78%, transparent);
  border-radius: 2px;
  background: color-mix(in srgb, var(--background-white-main) 10%, transparent);
  padding: 10px;
  margin-bottom: 8px;
}

.metric-row--ok {
  border-left: 3px solid #2eb67d;
}

.metric-row--warn {
  border-left: 3px solid #f59e0b;
}

.metric-row--critical {
  border-left: 3px solid #ef4444;
}

.metric-track {
  height: 6px;
  border-radius: 999px;
  background: #d7e0ea;
  overflow: hidden;
}

.metric-track__inner {
  height: 100%;
  border-radius: 999px;
  background: #3ba6e8;
}

.trend-cell {
  border: 1px solid color-mix(in srgb, var(--border-main) 78%, transparent);
  background: color-mix(in srgb, var(--background-white-main) 10%, transparent);
  border-radius: 2px;
  padding: 8px 10px;
}

.trend-cell__label {
  font-size: 11px;
  color: var(--text-tertiary);
}

.trend-cell__value {
  margin-top: 4px;
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.trend-line {
  margin-top: 10px;
  height: 44px;
  display: flex;
  align-items: flex-end;
  gap: 5px;
}

.trend-line span {
  flex: 1;
  min-height: 8px;
  border-radius: 999px;
  background: #66bdf0;
}

.tab-btn {
  height: 30px;
  border-radius: 999px;
  border: 1px solid transparent;
  padding: 0 12px;
  font-size: 13px;
  color: var(--text-tertiary);
}

.tab-btn:hover {
  color: var(--text-primary);
  background: var(--fill-tsp-white-main);
}

.tab-btn--active {
  border-color: var(--border-main);
  background: var(--background-white-main);
  color: var(--text-primary);
  font-weight: 600;
}

.plugin-panel,
.twin-panel {
  border: 1px solid var(--border-main);
  background: var(--background-gray-main);
  border-radius: 4px;
  padding: 12px;
}

.plugin-hint {
  background: linear-gradient(180deg, var(--background-gray-main) 0%, #eef3f9 100%);
}

.node-input {
  height: 36px;
  border-radius: 2px;
  border: 1px solid var(--border-main);
  background: var(--background-white-main);
  color: var(--text-primary);
  padding: 0 10px;
  font-size: 13px;
  outline: none;
}

.node-input:focus {
  border-color: #7ab5e8;
}

.node-save-btn {
  height: 34px;
  border-radius: 2px;
  padding: 0 12px;
  color: var(--text-onblack);
  background: var(--Button-primary-black);
  font-size: 13px;
  font-weight: 600;
}

.log-card {
  border-radius: 12px;
  border: 1px solid var(--border-main);
  background: var(--background-gray-main);
  padding: 10px;
}

.log-block {
  border-radius: 8px;
  border: 1px solid #d5dde8;
  background: #f7fafc;
  color: #203345;
  font-size: 12px;
  line-height: 1.55;
  padding: 8px;
  white-space: pre-wrap;
}

@media (max-width: 1024px) {
  .node-page {
    padding-left: 12px;
    padding-right: 12px;
  }

  .trend-cell__value {
    font-size: 21px;
  }
}

@media (min-width: 1025px) {
  .node-grid-sep > *::after {
    display: block;
  }
}
</style>
