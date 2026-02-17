<template>
  <div class="h-full w-full overflow-auto px-5 py-4">
    <div class="mb-3">
      <button
        v-if="!isLeftPanelShow"
        class="flex h-8 w-8 items-center justify-center cursor-pointer rounded-md border border-[var(--border-main)] bg-[var(--background-white-main)] hover:bg-[var(--fill-tsp-gray-main)]"
        @click="toggleLeftPanel"
      >
        <PanelLeft class="size-5 text-[var(--icon-secondary)]" />
      </button>
    </div>
    <div class="w-full">
      <div class="flex items-end justify-between mb-4 gap-4">
        <div>
          <div class="text-[24px] font-semibold text-[var(--text-primary)]">工单 Dashboard</div>
          <div class="text-sm text-[var(--text-tertiary)] mt-1">统一管理 AI 与人工协作工单。</div>
        </div>
        <button class="h-9 px-4 rounded-lg bg-[var(--Button-primary-black)] text-[var(--text-onblack)] text-sm" @click="showCreateDialog = true">
          新建工单
        </button>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
        <div v-for="card in metrics" :key="card.label" class="rounded-xl border border-[var(--border-main)] bg-[var(--background-card)] p-3">
          <div class="text-xs text-[var(--text-tertiary)]">{{ card.label }}</div>
          <div class="text-xl font-semibold text-[var(--text-primary)] mt-1">{{ card.value }}</div>
        </div>
      </div>

      <div class="rounded-xl border border-[var(--border-main)] bg-[var(--background-card)] p-3 mb-3 grid grid-cols-1 md:grid-cols-5 gap-2">
        <input v-model="filters.q" class="border rounded px-2 py-1.5 text-sm md:col-span-2" placeholder="搜索标题/描述/编号" />
        <select v-model="filters.status" class="border rounded px-2 py-1.5 text-sm">
          <option value="">全部状态</option>
          <option value="open">待处理</option>
          <option value="processing">处理中</option>
          <option value="waiting_user">待补充</option>
          <option value="resolved">已完成</option>
        </select>
        <select v-model="filters.priority" class="border rounded px-2 py-1.5 text-sm">
          <option value="">全部优先级</option>
          <option value="p0">P0</option>
          <option value="p1">P1</option>
          <option value="p2">P2</option>
          <option value="p3">P3</option>
        </select>
        <select v-model="filters.urgency" class="border rounded px-2 py-1.5 text-sm">
          <option value="">全部紧急度</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-3">
        <button
          v-for="ticket in filteredTickets"
          :key="ticket.ticket_id"
          class="text-left p-4 rounded-xl border border-[var(--border-main)] bg-[var(--background-card)] hover:bg-[var(--fill-tsp-gray-main)]"
          @click="openTicket(ticket.ticket_id)"
        >
          <div class="flex items-start justify-between gap-3 min-w-0">
            <div class="min-w-0 flex-1">
              <div class="font-medium text-[var(--text-primary)] truncate">{{ ticket.title || '未命名工单' }}</div>
              <div class="text-xs text-[var(--text-tertiary)] mt-1">#{{ ticket.ticket_id }} · {{ formatDate(ticket.updated_at) }}</div>
            </div>
            <div class="flex items-center gap-1 flex-wrap justify-end shrink-0">
              <span class="text-xs px-2 py-1 rounded whitespace-nowrap leading-4" :class="priorityClass(ticket.priority)">{{ ticket.priority.toUpperCase() }}</span>
              <span class="text-xs px-2 py-1 rounded whitespace-nowrap leading-4" :class="urgencyClass(ticket.urgency)">{{ ticket.urgency }}</span>
              <span class="text-xs px-2 py-1 rounded whitespace-nowrap leading-4" :class="statusClass(ticket.status)">{{ statusText(ticket.status) }}</span>
            </div>
          </div>
          <div class="text-sm text-[var(--text-tertiary)] mt-2 line-clamp-2">{{ ticket.description }}</div>
          <div class="flex items-center gap-2 mt-3 flex-wrap">
            <span v-for="tag in ticket.tags" :key="tag" class="text-xs px-2 py-1 rounded-full bg-zinc-100 text-zinc-700">{{ tag }}</span>
          </div>
        </button>
        <div v-if="filteredTickets.length === 0" class="h-[220px] xl:col-span-2 2xl:col-span-3 rounded-xl border border-dashed border-[var(--border-main)] flex items-center justify-center text-sm text-[var(--text-tertiary)]">
          当前筛选下没有工单。
        </div>
      </div>
    </div>
  </div>

  <div v-if="showCreateDialog" class="fixed inset-0 z-[80] bg-black/40 flex items-center justify-center p-4">
    <div class="w-full max-w-[760px] rounded-xl bg-white border border-[var(--border-main)] p-4">
      <div class="text-base font-semibold mb-3">新建工单</div>
      <div class="space-y-3">
        <div>
          <div class="text-xs text-[var(--text-tertiary)] mb-1">标题</div>
          <input v-model="form.title" class="w-full border rounded px-3 py-2 text-sm" placeholder="例如：排查 API 500 错误" />
        </div>
        <div>
          <div class="text-xs text-[var(--text-tertiary)] mb-1">描述</div>
          <textarea v-model="form.description" rows="5" class="w-full border rounded px-3 py-2 text-sm" placeholder="描述问题现象、预期结果、复现路径"></textarea>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <div class="text-xs text-[var(--text-tertiary)] mb-1">优先级</div>
            <select v-model="form.priority" class="w-full border rounded px-2 py-2 text-sm">
              <option value="p0">P0</option>
              <option value="p1">P1</option>
              <option value="p2">P2</option>
              <option value="p3">P3</option>
            </select>
          </div>
          <div>
            <div class="text-xs text-[var(--text-tertiary)] mb-1">紧急程度</div>
            <select v-model="form.urgency" class="w-full border rounded px-2 py-2 text-sm">
              <option value="critical">critical</option>
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
            </select>
          </div>
          <div>
            <div class="text-xs text-[var(--text-tertiary)] mb-1">预估工时(分钟)</div>
            <input v-model.number="form.estimated_minutes" type="number" min="0" class="w-full border rounded px-2 py-2 text-sm" />
          </div>
          <div>
            <div class="text-xs text-[var(--text-tertiary)] mb-1">SLA(小时)</div>
            <input v-model.number="form.sla_hours" type="number" min="1" class="w-full border rounded px-2 py-2 text-sm" />
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <div class="text-xs text-[var(--text-tertiary)] mb-1">标签（可创建）</div>
            <div class="border rounded px-2 py-2 min-h-[42px] flex flex-wrap gap-1 items-center">
              <span
                v-for="tag in form.tags"
                :key="tag"
                class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-zinc-100 text-zinc-700"
              >
                {{ tag }}
                <button class="text-zinc-500 hover:text-zinc-800" @click.prevent="removeTag(tag)">×</button>
              </span>
              <input
                v-model="newTagInput"
                class="flex-1 min-w-[100px] outline-none text-sm"
                placeholder="输入后回车创建标签"
                @keydown.enter.prevent="createTag"
              />
            </div>
            <div class="mt-2 flex flex-wrap gap-1">
              <button
                v-for="tag in availableTagOptions"
                :key="`tag-${tag}`"
                class="text-xs px-2 py-1 rounded-full border"
                :class="form.tags.includes(tag) ? 'bg-zinc-900 text-white border-zinc-900' : 'bg-white text-zinc-700 border-zinc-300'"
                @click="toggleTag(tag)"
              >
                {{ tag }}
              </button>
            </div>
          </div>
          <div>
            <div class="text-xs text-[var(--text-tertiary)] mb-1">关联节点（多选）</div>
            <div class="border rounded px-2 py-2 min-h-[42px] flex flex-wrap gap-1">
              <button
                v-for="node in availableNodes"
                :key="node.node_id"
                class="text-xs px-2 py-1 rounded border"
                :class="form.node_ids.includes(node.node_id) ? 'bg-zinc-900 text-white border-zinc-900' : 'bg-white text-zinc-700 border-zinc-300'"
                @click="toggleNode(node.node_id)"
              >
                {{ node.name }}
              </button>
              <span v-if="availableNodes.length === 0" class="text-xs text-[var(--text-tertiary)]">暂无可选节点</span>
            </div>
          </div>
          <div>
            <div class="text-xs text-[var(--text-tertiary)] mb-1">关联插件（多选）</div>
            <div class="border rounded px-2 py-2 min-h-[42px] flex flex-wrap gap-1">
              <button
                v-for="plugin in availablePlugins"
                :key="plugin"
                class="text-xs px-2 py-1 rounded border"
                :class="form.plugin_ids.includes(plugin) ? 'bg-zinc-900 text-white border-zinc-900' : 'bg-white text-zinc-700 border-zinc-300'"
                @click="togglePlugin(plugin)"
              >
                {{ plugin }}
              </button>
            </div>
          </div>
        </div>
      </div>
      <div class="flex justify-end gap-2 mt-4">
        <button class="px-3 py-1.5 border rounded" @click="showCreateDialog = false; resetCreateForm()">取消</button>
        <button class="px-3 py-1.5 rounded bg-[var(--Button-primary-black)] text-[var(--text-onblack)]" :disabled="creating" @click="submitCreate">
          {{ creating ? '创建中...' : '创建并派发' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { PanelLeft } from 'lucide-vue-next';
import {
  createTicket,
  listTickets,
  type CreateTicketRequest,
  type TicketItem,
  type TicketPriority,
  type TicketStatus,
  type TicketUrgency,
} from '@/api/ticket';
import { listServerNodes, type ServerNode } from '@/api/node';
import { useLeftPanel } from '@/composables/useLeftPanel';
import { showErrorToast, showSuccessToast } from '@/utils/toast';

const router = useRouter();
const route = useRoute();
const { isLeftPanelShow, toggleLeftPanel } = useLeftPanel();

const tickets = ref<TicketItem[]>([]);
const availableNodes = ref<ServerNode[]>([]);
const newTagInput = ref('');
const showCreateDialog = ref(false);
const creating = ref(false);
const baseTagOptions = ref<string[]>(['api', 'prod', 'bug', 'urgent', 'infra', 'security']);
const availablePlugins = ['shell', 'file', 'browser', 'search', 'mcp', 'ssh', 'ticket'];

const filters = reactive({
  q: '',
  status: '',
  priority: '',
  urgency: '',
});

const form = reactive<{
  title: string;
  description: string;
  priority: TicketPriority;
  urgency: TicketUrgency;
  estimated_minutes?: number;
  sla_hours?: number;
  tags: string[];
  node_ids: string[];
  plugin_ids: string[];
}>({
  title: '',
  description: '',
  priority: 'p2',
  urgency: 'medium',
  estimated_minutes: undefined,
  sla_hours: undefined,
  tags: [],
  node_ids: [],
  plugin_ids: [],
});

const formatDate = (value: string): string => {
  const date = new Date(value);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
};

const statusText = (status: TicketStatus): string => {
  if (status === 'open') return '待处理';
  if (status === 'processing') return '处理中';
  if (status === 'waiting_user') return '待补充';
  return '已完成';
};

const statusClass = (status: TicketStatus): string => {
  if (status === 'open') return 'bg-zinc-100 text-zinc-700';
  if (status === 'processing') return 'bg-amber-100 text-amber-700';
  if (status === 'waiting_user') return 'bg-sky-100 text-sky-700';
  return 'bg-emerald-100 text-emerald-700';
};

const priorityClass = (priority: TicketPriority): string => {
  if (priority === 'p0') return 'bg-red-100 text-red-700';
  if (priority === 'p1') return 'bg-orange-100 text-orange-700';
  if (priority === 'p2') return 'bg-blue-100 text-blue-700';
  return 'bg-zinc-100 text-zinc-700';
};

const urgencyClass = (urgency: TicketUrgency): string => {
  if (urgency === 'critical') return 'bg-red-100 text-red-700';
  if (urgency === 'high') return 'bg-amber-100 text-amber-700';
  if (urgency === 'medium') return 'bg-sky-100 text-sky-700';
  return 'bg-zinc-100 text-zinc-700';
};

const filteredTickets = computed(() => {
  const q = filters.q.trim().toLowerCase();
  return tickets.value.filter((ticket) => {
    if (filters.status && ticket.status !== filters.status) return false;
    if (filters.priority && ticket.priority !== filters.priority) return false;
    if (filters.urgency && ticket.urgency !== filters.urgency) return false;
    if (!q) return true;
    return (
      ticket.ticket_id.toLowerCase().includes(q) ||
      ticket.title.toLowerCase().includes(q) ||
      ticket.description.toLowerCase().includes(q)
    );
  });
});

const metrics = computed(() => {
  const total = tickets.value.length;
  const open = tickets.value.filter((t) => t.status === 'open').length;
  const processing = tickets.value.filter((t) => t.status === 'processing').length;
  const waiting = tickets.value.filter((t) => t.status === 'waiting_user').length;
  const overdue = tickets.value.filter((t) => t.sla_due_at && new Date(t.sla_due_at).getTime() < Date.now() && t.status !== 'resolved').length;
  return [
    { label: '总工单', value: total },
    { label: '待处理', value: open },
    { label: '处理中', value: processing },
    { label: '待补充', value: waiting },
    { label: '已逾期', value: overdue },
  ];
});

const availableTagOptions = computed(() => {
  const fromTickets = tickets.value.flatMap((ticket) => ticket.tags || []);
  return Array.from(new Set([...baseTagOptions.value, ...fromTickets]));
});

const toggleTag = (tag: string): void => {
  if (form.tags.includes(tag)) {
    form.tags = form.tags.filter((item) => item !== tag);
  } else {
    form.tags = [...form.tags, tag];
  }
};

const removeTag = (tag: string): void => {
  form.tags = form.tags.filter((item) => item !== tag);
};

const createTag = (): void => {
  const value = newTagInput.value.trim();
  if (!value) return;
  if (!baseTagOptions.value.includes(value)) {
    baseTagOptions.value = [...baseTagOptions.value, value];
  }
  if (!form.tags.includes(value)) {
    form.tags = [...form.tags, value];
  }
  newTagInput.value = '';
};

const toggleNode = (nodeId: string): void => {
  if (form.node_ids.includes(nodeId)) {
    form.node_ids = form.node_ids.filter((item) => item !== nodeId);
  } else {
    form.node_ids = [...form.node_ids, nodeId];
  }
};

const togglePlugin = (pluginId: string): void => {
  if (form.plugin_ids.includes(pluginId)) {
    form.plugin_ids = form.plugin_ids.filter((item) => item !== pluginId);
  } else {
    form.plugin_ids = [...form.plugin_ids, pluginId];
  }
};

const resetCreateForm = (): void => {
  form.title = '';
  form.description = '';
  form.priority = 'p2';
  form.urgency = 'medium';
  form.estimated_minutes = undefined;
  form.sla_hours = undefined;
  form.tags = [];
  form.node_ids = [];
  form.plugin_ids = [];
  newTagInput.value = '';
};

const loadNodes = async (): Promise<void> => {
  try {
    availableNodes.value = await listServerNodes();
  } catch (error) {
    console.error('Failed to load nodes', error);
    availableNodes.value = [];
  }
};

const reloadTickets = async (): Promise<void> => {
  try {
    tickets.value = await listTickets();
  } catch (error) {
    console.error('Failed to load tickets', error);
    showErrorToast('加载工单失败');
  }
};

const openTicket = (ticketId: string): void => {
  router.push(`/chat/tickets/${ticketId}`);
};

const submitCreate = async (): Promise<void> => {
  if (!form.title.trim() || !form.description.trim()) {
    showErrorToast('请填写标题和描述');
    return;
  }
  creating.value = true;
  try {
    const payload: CreateTicketRequest = {
      title: form.title.trim(),
      description: form.description.trim(),
      priority: form.priority,
      urgency: form.urgency,
      estimated_minutes: form.estimated_minutes,
      sla_hours: form.sla_hours,
      tags: form.tags,
      node_ids: form.node_ids,
      plugin_ids: form.plugin_ids,
    };
    const created = await createTicket(payload);
    showCreateDialog.value = false;
    resetCreateForm();
    await reloadTickets();
    showSuccessToast('工单已创建并派发给 AI');
    openTicket(created.ticket_id);
  } catch (error) {
    console.error('Failed to create ticket', error);
    showErrorToast('创建工单失败');
  } finally {
    creating.value = false;
  }
};

onMounted(async () => {
  await reloadTickets();
  await loadNodes();
  if (route.query.create === '1') {
    showCreateDialog.value = true;
  }
});

watch(
  () => route.query.create,
  (createFlag) => {
    if (createFlag === '1') {
      showCreateDialog.value = true;
    }
  }
);
</script>
