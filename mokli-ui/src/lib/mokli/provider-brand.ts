/** Official provider marks, same sources as the legacy Models page. */

export type ProviderLogo = {
	logoUrls: string[];
	color: string;
	initials: string;
};

function faviconIm(domain: string): string {
	return `https://favicon.im/${encodeURIComponent(domain)}?larger=true`;
}

function googleFavicon(domain: string): string {
	return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`;
}

function duckDuckGoFavicon(domain: string): string {
	return `https://icons.duckduckgo.com/ip3/${encodeURIComponent(domain)}.ico`;
}

function officialFavicon(domain: string): string {
	return `https://${domain}/favicon.ico`;
}

function brand(domain: string, color: string, initials: string, extra: string[] = []): ProviderLogo {
	const host = domain.split('/')[0] || domain;
	const logoUrls = [
		...extra,
		faviconIm(host),
		googleFavicon(domain),
		duckDuckGoFavicon(host),
		officialFavicon(host)
	];
	return { logoUrls, color, initials };
}

const ALIASES: Record<string, string> = {
	brave_search: 'brave',
	byteplus_coding_plan: 'byteplus',
	claude_code_cli: 'anthropic',
	mimo: 'xiaomi_mimo',
	minimaxAnthropic: 'minimax',
	minimax_anthropic: 'minimax',
	openai_codex: 'openai',
	'xai-grok': 'xai',
	xai_grok: 'xai',
	xiaomi: 'xiaomi_mimo',
	volcengine_coding_plan: 'volcengine'
};

const BRANDS: Record<string, ProviderLogo> = {
	aihubmix: brand('aihubmix.com', '#111827', 'AH'),
	ant_ling: brand('ant-ling.com', '#7C3AED', 'AL'),
	anthropic: brand('anthropic.com', '#D97757', 'A'),
	assemblyai: brand('assemblyai.com', '#111827', 'AA'),
	atomic_chat: brand('atomic.chat', '#111827', 'AC'),
	azure_openai: brand('azure.microsoft.com', '#0078D4', 'AZ'),
	bedrock: brand('aws.amazon.com', '#FF9900', 'AWS'),
	bocha: brand('bochaai.com', '#2563EB', 'B'),
	brave: brand('brave.com', '#FB542B', 'B'),
	byteplus: brand('byteplus.com', '#325CFF', 'BP'),
	dashscope: brand('dashscope.aliyun.com', '#FF6A00', 'DS'),
	deepseek: brand('deepseek.com', '#4D6BFE', 'DS'),
	duckduckgo: brand('duckduckgo.com', '#DE5833', 'DDG'),
	exa: brand('exa.ai', '#5B5BF6', 'E'),
	gemini: brand('gemini.google.com', '#4285F4', 'G'),
	github_copilot: brand('github.com', '#24292F', 'GH'),
	groq: brand('groq.com', '#F55036', 'GQ'),
	huggingface: brand('huggingface.co', '#FF9D00', 'HF'),
	jina: brand('jina.ai', '#7C3AED', 'J'),
	kagi: brand('kagi.com', '#FFB319', 'K'),
	keenable: brand('keenable.ai', '#0EA5E9', 'K'),
	lm_studio: brand('lmstudio.ai', '#111827', 'LM'),
	longcat: brand('longcatai.org', '#4F8CFF', 'LC', ['https://www.longcatai.org/favicon.svg']),
	minimax: brand('minimax.io', '#111827', 'MM'),
	mistral: brand('mistral.ai', '#FA520F', 'M'),
	modelscope: brand('modelscope.cn', '#5B5BF6', 'MS'),
	moonshot: brand('moonshot.ai', '#111827', 'MS'),
	novita: brand('novita.ai', '#7C3AED', 'N'),
	olostep: brand('olostep.com', '#111827', 'O'),
	nvidia: brand('nvidia.com', '#76B900', 'NV'),
	ollama: brand('ollama.com', '#111827', 'O'),
	openai: brand('openai.com', '#111827', 'AI'),
	openrouter: brand('openrouter.ai', '#111827', 'OR'),
	orcarouter: brand('orcarouter.ai', '#111827', 'OR'),
	ovms: brand('openvino.ai', '#0071C5', 'OV'),
	qianfan: brand('cloud.baidu.com', '#2932E1', 'QF'),
	searxng: brand('searxng.org', '#3050FF', 'SX'),
	siliconflow: brand('siliconflow.cn', '#111827', 'SF'),
	skywork: brand('skywork.ai', '#5B5BF6', 'SW'),
	stepfun: brand('stepfun.com', '#2F6BFF', 'SF', ['https://www.stepfun.com/step_favicon.svg']),
	tavily: brand('tavily.com', '#111827', 'T'),
	volcengine: brand('volcengine.com', '#1664FF', 'VE'),
	vllm: brand('vllm.ai', '#2563EB', 'VL'),
	xiaomi_mimo: brand('mimo.xiaomi.com', '#FF6900', 'MI', [
		'https://mimo.xiaomi.com/mimo-v2-pro/assets/logo.svg'
	]),
	xai: brand('x.ai', '#111827', 'xAI'),
	zhipu: brand('z.ai', '#155EEF', 'Z', [
		'https://z-cdn.chatglm.cn/z-ai/static/logo.svg',
		'https://www.google.com/s2/favicons?domain=z.ai&sz=64'
	])
};

export function providerLogo(name: string | null | undefined): ProviderLogo | null {
	if (!name) return null;
	const key = ALIASES[name] ?? name;
	return BRANDS[key] ?? null;
}
