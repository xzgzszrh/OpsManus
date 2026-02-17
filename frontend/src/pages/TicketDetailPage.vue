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
    <div class="w-full" v-if="ticket">
      <div class="flex items-center justify-between gap-3 mb-3">
        <div class="min-w-0 flex-1">
          <button class="text-sm text-[var(--text-tertiary)] hover:text-[var(--text-primary)]" @click="router.push('/chat/tickets')">← 返回工单 Dashboard</button>
          <div class="text-[24px] font-semibold text-[var(--text-primary)] mt-1 truncate">{{ ticket.title || '未命名工单' }}</div>
          <div class="text-xs text-[var(--text-tertiary)] mt-1">#{{ ticket.ticket_id }} · 创建于 {{ formatDate(ticket.created_at) }}</div>
        </div>
        <div class="flex items-center gap-2">
          <button class="px-3 py-1.5 border rounded text-sm" @click="openSession(ticket.session_id)">查看后台对话</button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div class="lg:col-span-8 space-y-4">
          <section class="rounded-xl border border-[var(--border-main)] bg-[var(--background-card)] p-4">
            <div class="text-sm font-medium mb-2">问题描述</div>
            <div class="text-sm whitespace-pre-wrap text-[var(--text-primary)]">{{ ticket.description }}</div>
          </section>

          <section class="rounded-xl border border-[var(--border-main)] bg-[var(--background-card)] p-4">
            <div class="text-sm font-medium mb-3">沟通记录</div>
            <div class="space-y-2 max-h-[320px] overflow-auto pr-1">
              <div v-for="comment in ticket.comments" :key="comment.comment_id" class="rounded-lg border p-2">
                <div class="text-xs text-[var(--text-tertiary)] mb-1">{{ roleText(comment.role) }} · {{ formatDate(comment.created_at) }}</div>
                <div class="text-sm whitespace-pre-wrap">{{ comment.message }}</div>
              </div>
            </div>
            <div class="mt-3 border-t pt-3">
              <div class="text-xs text-[var(--text-tertiary)] mb-1">补充信息</div>
              <textarea v-model="replyMessage" rows="4" class="w-full border rounded px-3 py-2 text-sm" placeholder="补充上下文、日志、复现结果" />
              <div class="flex justify-end mt-2">
                <button class="px-3 py-1.5 rounded bg-[var(--Button-primary-black)] text-[var(--text-onblack)] text-sm" :disabled="replying" @click="submitReply">
                  {{ replying ? '发送中...' : '提交回复' }}
                </button>
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-[var(--border-main)] bg-[var(--background-card)] p-4">
            <div class="text-sm font-medium mb-3">工单时间线</div>
            <div class="space-y-2 max-h-[280px] overflow-auto pr-1">
              <div v-for="event in ticket.events" :key="event.event_id" class="rounded-lg border p-2">
                <div class="text-xs text-[var(--text-tertiary)]">{{ event.event_type }} · {{ formatDate(event.created_at) }}</div>
                <div class="text-sm mt-1">{{ event.message }}</div>
              </div>
            </div>
          </section>
        </div>

        <div class="lg:col-span-4 space-y-4">
          <section class="rounded-xl border border-[var(--border-main)] bg-[var(--background-card)] p-4 space-y-3">
            <div class="text-sm font-medium">工单属性</div>
            <div>
              <div class="text-xs text-[var(--text-tertiary)] mb-1">状态</div>
              <select v-model="editable.status" class="w-full border rounded px-2 py-2 text-sm">
                <option value="open">待处理</option>
                <option value="processing">处理中</option>
                <option value="waiting_user">待补充</option>
                <option value="resolved">已完成</option>
              </select>
            </div>
            <div>
              <div class="text-xs text-[var(--text-tertiary)] mb-1">优先级</div>
              <select v-model="editable.priority" class="w-full border rounded px-2 py-2 text-sm">
                <option value="p0">P0</option>
                <option value="p1">P1</option>
                <option value="p2">P2</option>
                <option value="p3">P3</option>
              </select>
            </div>
            <div>
              <div class="text-xs text-[var(--text-tertiary)] mb-1">紧急程度</div>
              <select v-model="editable.urgency" class="w-full border rounded px-2 py-2 text-sm">
                <option value="critical">critical</option>
                <option value="high">high</option>
                <option value="medium">medium</option>
                <option value="low">low</option>
              </select>
            </div>
            <div>
              <div class="text-xs text-[var(--text-tertiary)] mb-1">标签（逗号）</div>
              <input v-model="editable.tags" class="w-full border rounded px-2 py-2 text-sm" />
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <div class="text-xs text-[var(--text-tertiary)] mb-1">预估工时</div>
                <input v-model.number="editable.estimated_minutes" type="number" min="0" class="w-full border rounded px-2 py-2 text-sm" />
              </div>
              <div>
                <div class="text-xs text-[var(--text-tertiary)] mb-1">已耗时</div>
                <input v-model.number="editable.spent_minutes" type="number" min="0" class="w-full border rounded px-2 py-2 text-sm" />
              </div>
            </div>
            <button class="w-full px-3 py-2 rounded bg-[var(--Button-primary-black)] text-[var(--text-onblack)] text-sm" :disabled="saving" @click="saveMeta">
              {{ saving ? '保存中...' : '保存属性' }}
            </button>
          </section>

          <section class="rounded-xl border border-[var(--border-main)] bg-[var(--background-card)] p-4">
            <div class="text-sm font-medium mb-2">协作信息</div>
            <div class="text-xs text-[var(--text-tertiary)] space-y-1">
              <div>SLA 截止: {{ ticket.sla_due_at ? formatDate(ticket.sla_due_at) : '-' }}</div>
              <div>首次响应: {{ ticket.first_response_at ? formatDate(ticket.first_response_at) : '-' }}</div>
              <div>解决时间: {{ ticket.resolved_at ? formatDate(ticket.resolved_at) : '-' }}</div>
              <div>重开次数: {{ ticket.reopen_count }}</div>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { PanelLeft } from 'lucide-vue-next';
import { getTicket, replyTicket, updateTicket, type TicketCommentRole, type TicketItem } from '@/api/ticket';
import { useLeftPanel } from '@/composables/useLeftPanel';
import { showErrorToast, showSuccessToast } from '@/utils/toast';

const route = useRoute();
const router = useRouter();
const { isLeftPanelShow, toggleLeftPanel } = useLeftPanel();

const ticket = ref<TicketItem | null>(null);
const replyMessage = ref('');
const replying = ref(false);
const saving = ref(false);

const editable = reactive({
  status: 'open',
  priority: 'p2',
  urgency: 'medium',
  tags: '',
  estimated_minutes: 0,
  spent_minutes: 0,
});

const parseCsv = (value: string): string[] => value.split(',').map((v) => v.trim()).filter((v) => v.length > 0);

const formatDate = (value: string): string => {
  const date = new Date(value);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
};

const roleText = (role: TicketCommentRole): string => {
  if (role === 'user') return '用户';
  if (role === 'ai') return 'AI';
  return '系统';
};

const loadTicket = async (): Promise<void> => {
  const ticketId = route.params.ticketId;
  if (typeof ticketId !== 'string' || !ticketId) return;
  try {
    const data = await getTicket(ticketId);
    ticket.value = data;
    editable.status = data.status;
    editable.priority = data.priority;
    editable.urgency = data.urgency;
    editable.tags = data.tags.join(',');
    editable.estimated_minutes = data.estimated_minutes || 0;
    editable.spent_minutes = data.spent_minutes;
  } catch (error) {
    console.error('Failed to load ticket detail', error);
    showErrorToast('加载工单详情失败');
  }
};

const submitReply = async (): Promise<void> => {
  if (!ticket.value) return;
  const msg = replyMessage.value.trim();
  if (!msg) {
    showErrorToast('请输入回复内容');
    return;
  }
  replying.value = true;
  try {
    ticket.value = await replyTicket(ticket.value.ticket_id, msg);
    replyMessage.value = '';
    showSuccessToast('已提交回复并通知 AI 继续处理');
  } catch (error) {
    console.error('Failed to submit reply', error);
    showErrorToast('提交回复失败');
  } finally {
    replying.value = false;
  }
};

const saveMeta = async (): Promise<void> => {
  if (!ticket.value) return;
  saving.value = true;
  try {
    ticket.value = await updateTicket(ticket.value.ticket_id, {
      status: editable.status as TicketItem['status'],
      priority: editable.priority as TicketItem['priority'],
      urgency: editable.urgency as TicketItem['urgency'],
      tags: parseCsv(editable.tags),
      estimated_minutes: editable.estimated_minutes,
      spent_minutes: editable.spent_minutes,
    });
    showSuccessToast('工单属性已更新');
  } catch (error) {
    console.error('Failed to update ticket', error);
    showErrorToast('更新工单失败');
  } finally {
    saving.value = false;
  }
};

const openSession = (sessionId: string): void => {
  router.push(`/chat/${sessionId}`);
};

onMounted(loadTicket);
watch(() => route.params.ticketId, loadTicket);
</script>
