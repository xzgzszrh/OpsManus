export interface ParsedMCPFunction {
  serverId: string;
  serverAlias: 'vision' | 'search' | 'reader' | 'zread' | 'generic';
  toolName: string;
  rawFunction: string;
}

export interface MCPLinkItem {
  title: string;
  url: string;
  snippet?: string;
  icon?: string;
}

export interface ParsedMCPResult {
  parsed: any;
  text: string;
  links: MCPLinkItem[];
  title?: string;
  description?: string;
  content?: string;
}

const SERVER_ALIASES: { prefixes: string[]; alias: ParsedMCPFunction['serverAlias'] }[] = [
  { prefixes: ['bigmodel_vision', 'zai_vision', 'vision'], alias: 'vision' },
  { prefixes: ['bigmodel_search', 'web_search_prime', 'search'], alias: 'search' },
  { prefixes: ['bigmodel_reader', 'web_reader', 'reader'], alias: 'reader' },
  { prefixes: ['bigmodel_zread', 'zread'], alias: 'zread' },
];

function tryParseJson(value: string): any {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function parseDeepJson(input: any, maxDepth: number = 4): any {
  let current = input;
  for (let i = 0; i < maxDepth; i++) {
    if (typeof current !== 'string') break;
    const trimmed = current.trim();
    if (!trimmed) break;
    const next = tryParseJson(trimmed);
    if (next === current) break;
    current = next;
  }
  return current;
}

function pickLink(item: any): MCPLinkItem | null {
  if (!item || typeof item !== 'object') return null;
  const url = String(item.url || item.link || item.href || '').trim();
  if (!url) return null;
  return {
    title: String(item.title || item.name || item.site || url),
    url,
    snippet: item.snippet || item.summary || item.description || item.content,
    icon: item.icon || item.favicon,
  };
}

function extractLinksFromArray(items: any[]): MCPLinkItem[] {
  const links: MCPLinkItem[] = [];
  for (const item of items) {
    const link = pickLink(item);
    if (link) links.push(link);
  }
  return links;
}

function extractLinksFromObject(obj: any): MCPLinkItem[] {
  if (!obj || typeof obj !== 'object') return [];
  const candidateArrays = [obj.results, obj.items, obj.data, obj.links, obj.web_pages, obj.search_result];
  for (const arr of candidateArrays) {
    if (Array.isArray(arr)) {
      const links = extractLinksFromArray(arr);
      if (links.length > 0) return links;
    }
  }
  const single = pickLink(obj);
  return single ? [single] : [];
}

function extractLinksByRegex(text: string): MCPLinkItem[] {
  const regex = /(https?:\/\/[^\s)\]"'>]+)/g;
  const set = new Set<string>();
  const links: MCPLinkItem[] = [];
  for (const match of text.matchAll(regex)) {
    const url = match[1];
    if (!set.has(url)) {
      set.add(url);
      links.push({ title: url, url });
    }
  }
  return links;
}

function normalizeResultText(result: any): string {
  if (typeof result === 'string') return result;
  if (result === null || result === undefined) return '';
  if (typeof result === 'number' || typeof result === 'boolean') return String(result);
  try {
    return JSON.stringify(result, null, 2);
  } catch {
    return String(result);
  }
}

export function parseMCPResult(rawResult: any): ParsedMCPResult {
  const parsed = parseDeepJson(rawResult);
  const text = normalizeResultText(parsed);

  let links: MCPLinkItem[] = [];
  if (Array.isArray(parsed)) {
    links = extractLinksFromArray(parsed);
  } else if (parsed && typeof parsed === 'object') {
    links = extractLinksFromObject(parsed);
  }
  if (links.length === 0 && text) {
    links = extractLinksByRegex(text);
  }

  const title = parsed && typeof parsed === 'object' ? (parsed.title || parsed.name) : undefined;
  const description = parsed && typeof parsed === 'object' ? (parsed.description || parsed.summary) : undefined;
  const content = parsed && typeof parsed === 'object' ? parsed.content : undefined;

  return { parsed, text, links, title, description, content };
}

export function parseMCPFunction(functionName: string): ParsedMCPFunction {
  const raw = functionName.startsWith('mcp_') ? functionName.slice(4) : functionName;

  for (const candidate of SERVER_ALIASES) {
    for (const prefix of candidate.prefixes) {
      if (raw.startsWith(`${prefix}_`)) {
        return {
          serverId: prefix,
          serverAlias: candidate.alias,
          toolName: raw.slice(prefix.length + 1),
          rawFunction: raw,
        };
      }
      if (raw === prefix) {
        return {
          serverId: prefix,
          serverAlias: candidate.alias,
          toolName: prefix,
          rawFunction: raw,
        };
      }
    }
  }

  const idx = raw.indexOf('_');
  if (idx > 0) {
    return {
      serverId: raw.slice(0, idx),
      serverAlias: 'generic',
      toolName: raw.slice(idx + 1),
      rawFunction: raw,
    };
  }

  return {
    serverId: 'unknown',
    serverAlias: 'generic',
    toolName: raw,
    rawFunction: raw,
  };
}

export function mcpServerLabelKey(alias: ParsedMCPFunction['serverAlias']): string {
  if (alias === 'vision') return 'BigModel Vision MCP';
  if (alias === 'search') return 'BigModel Search MCP';
  if (alias === 'reader') return 'BigModel Reader MCP';
  if (alias === 'zread') return 'BigModel ZRead MCP';
  return 'MCP Tool';
}
