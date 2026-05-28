export const RELIGIOUS_FALLBACK =
  "I can only help with Indian religion and spirituality. Please ask a related question.";
export const EDUCATION_FALLBACK =
  "I can only help with school and learning topics. Please ask an education-related question.";
export const DIGITAL_LITERACY_FALLBACK =
  "I can only help with AI and digital literacy topics. Please ask something related.";
export const DESIGN_THINKING_FALLBACK =
  "I can only help with design thinking and innovation topics. Please ask something related.";
export const WELLBEING_FALLBACK =
  "I can only help with well-being topics. Please ask something related.";
export const SUSTAINABILITY_FALLBACK =
  "I can only help with sustainability topics. Please ask something related.";
export const GLOBAL_CITIZENSHIP_FALLBACK =
  "I can only help with global citizenship topics. Please ask something related.";
export const ENTREPRENEURSHIP_FALLBACK =
  "I can only help with entrepreneurship topics. Please ask something related.";
export const EMOTIONAL_INTELLIGENCE_FALLBACK =
  "I can only help with emotional intelligence topics. Please ask something related.";
export const FINANCIAL_LITERACY_FALLBACK =
  "I can only help with financial literacy topics. Please ask something related.";

const ALWAYS_ALLOWED_INTENT_PATTERNS = [
  /\b(hi|hello|hey|namaste)\b/i,
  /\bgood\s+(morning|afternoon|evening)\b/i,
  /\b(how are you|who are you|what can you do|can you help me|help me)\b/i,
  /\b(thank you|thanks)\b/i,
];

/** Continuation / deictic follow-ups (reference prior answer in the same session). */
const FOLLOW_UP_CONTINUATION_PATTERNS = [
  /\b(tell me more|more about|more on|more details|any more|go (deeper|further)|elaborate|expand on|expand\b|continue|what about|what else|how about)\b/i,
  /\b(the same|that (one|topic|answer|point|part)|previous|above|you (just )?said|last (answer|point|part))\b/i,
  /\babout (him|her|it|them|this|that|those|one)\b/i,
];

const CLEAR_OFF_TOPIC_INTENT_PATTERNS = [
  /\b(write|generate|debug|fix|review)\b.*\b(code|program|script|bug)\b/i,
  /\b(weather|temperature|forecast)\b/i,
  /\b(stock|share market|crypto|bitcoin|trading|investment tip)\b/i,
  /\b(book|reserve)\b.*\b(flight|hotel|ticket)\b/i,
  /\b(movie|series|netflix|song|lyrics)\b/i,
  /\b(score|match|team|ipl|fifa|nba|football|cricket)\b/i,
  /\b(recipe|cook|cooking)\b/i,
  /\b(election|prime minister|parliament|vote for|politic|political party|us president|presidential|war in|invasion|sports betting|casino|lottery)\b/i,
];

// “Explain this” wording — shared; combined with subject lexicon in each domain.
const INQUIRY_PHRASE_PATTERN =
  /\b(tell\s+(me\s+)?about|what\s+is|what\s+are|what\s+was|how\s+(do|does|to|can|would|is|are)|describe|define|explain|why\s+(is|are|do|does)|difference\s+between|compare)\b/i;

const EDUCATION_INTENT_PATTERNS = [
  INQUIRY_PHRASE_PATTERN,
  /\b(explain|teach|learn|study|revise|practice|solve|prepare|summari[sz]e)\b/i,
  /\b(homework|assignment|exam|question|syllabus|chapter|subject|class|lesson|student|teacher)\b/i,

  /\b(math|mathematics|algebra|geometry|geometric|calculus|trigonometry|trignometry|equation|integral|derivative|formula|graph|theorem|proof)\b/i,
  /\b(science|history|geography|physics|chemistry|biology|english|grammar|college|university)\b/i,
  /\b(circle|circular|triangle|quadrilateral|polygon|pentagon|hexagon|angle|angles|radian|radians|degree|perpendicular|parallel|chord|arc|sector|cone|cylinder|sphere|prism|pyramid|radius|diameter|circumference|perimeter|area|volume|surface\s+area|coordinate|plane|sine|cosine|tangent|cotangent|cosecant|secant|trig|logarithm|exponent|quadratic|polynomial|inequality|matrix|vector|determinant|series|sequence|probability|statistics|acid|base|reaction|element|compound|mixture|motion|force|velocity|acceleration|energy|wave|electric|magnetic|circuit|novel|poem|literature|essay|vocabulary|comprehension|cbse|ncert|board\s+exam)\b/i,
];

const RELIGIOUS_INTENT_PATTERNS = [
  /\b(explain|meaning|significance|story|guide|chant|prayer|mantra|ritual|festival|verse)\b/i,
  /\b(gita|ramayan|ramayana|mahabharat|upanishad|veda|vedas|temple|puja|aarti|dharma|karma|moksha|bhakti|hindu|hinduism|sanatan|bhagavad|puran|purana|sanskrit|upanishadic)\b/i,
  /\b(spiritual|spirituality|meditation|yoga|shloka|sloka|stotra|stotram|krishna|krsna|ram|rama|sita|shiva|mahadev|hanuman|ganesh|ganapati|vishnu|brahma|lakshmi|saraswati|durga|kali|devi|swami|guru|sadhu|ashram|pilgrimage|yatra|worship|bhajan|kirtan|fasting|vrat)\b/i,
  /\b(diwali|deepavali|holi|navratri|dussehra|janmashtami|mahashivaratri|raksha\s+bandhan|pongal|onam)\b/i,
];

const DIGITAL_LITERACY_INTENT_PATTERNS = [
  /\b(ai|artificial intelligence|chatgpt|llm|machine learning|model)\b/i,
  /\b(digital|online|internet|web|social media|algorithm|recommendation)\b/i,
  /\b(privacy|phishing|scam|password|2fa|cyber|security|deepfake|data)\b/i,
  /\b(screen time|device|app safety|digital footprint)\b/i,
];

const DESIGN_THINKING_INTENT_PATTERNS = [
  /\b(design thinking|double diamond|empathize|empathy|ideate|prototype|test)\b/i,
  /\b(user research|journey map|pain point|how might we|brainstorm)\b/i,
  /\b(innovation|invention|creative solution|ux|ui)\b/i,
];

const WELLBEING_INTENT_PATTERNS = [
  /\b(well[- ]?being|wellness|self-care|habits|sleep|exercise|hydration|nutrition|energy|rest|fatigue|tired|exhausted)\b/i,
  /\b(stress|anxiety|calm|mindfulness|meditation|breathing|relax|relaxation|peace|peaceful|overwhelm|burnout)\b/i,
  /\b(friendship|kindness|boundaries|confidence|emotions|emotional|empathy)\b/i,
  // Feelings, moods, and emotional expressions students commonly use
  /\b(feel|feeling|feelings|felt|mood|moods)\b/i,
  /\b(sad|sadness|happy|happiness|angry|anger|scared|fear|afraid|worried|worry|worries|nervous|anxious|upset|frustrated|frustration|irritated|bored|boredom|jealous|jealousy|guilty|guilt|shame|embarrassed|confused|hopeless|hopeful|grateful|gratitude|excited|excitement)\b/i,
  /\b(lonely|loneliness|alone|isolated|left out|misunderstood|unloved|ignored|rejected|insecure|helpless|lost|stuck|unmotivated|lazy|distracted)\b/i,
  // Peer and social wellbeing
  /\b(bully|bullying|bullied|peer pressure|conflict|argument|fight|toxic|pressure|pressured|compare|comparison|self[- ]?esteem|self[- ]?worth|self[- ]?image|body image|self[- ]?doubt|growth mindset)\b/i,
  // Daily wellbeing and coping
  /\b(cope|coping|deal with|manage|managing|handle|handling|overcome|overcoming|balance|screen[- ]?time|routine|journal|journaling|motivation|motivated|positive|positivity|negative|negativity|mental health|healthy habits)\b/i,
];

const SUSTAINABILITY_INTENT_PATTERNS = [
  /\b(sustainability|sustainable|climate|environment|eco|ecology)\b/i,
  /\b(recycle|recycling|upcycling|carbon|emissions|renewable)\b/i,
  /\b(biodiversity|pollution|conservation|green energy)\b/i,
];

const GLOBAL_CITIZENSHIP_INTENT_PATTERNS = [
  /\b(global citizenship|sdg|human rights|diversity|inclusion)\b/i,
  /\b(culture|tradition|language|community|equality)\b/i,
  /\b(international|world|global|civic|ethics)\b/i,
];

const ENTREPRENEURSHIP_INTENT_PATTERNS = [
  /\b(entrepreneur|entrepreneurship|startup|business|founder)\b/i,
  /\b(idea|pitch|market|customer|pricing|revenue|profit)\b/i,
  /\b(branding|marketing|sales|mvp|prototype)\b/i,
];

const EMOTIONAL_INTELLIGENCE_INTENT_PATTERNS = [
  /\b(emotional intelligence|eq|empathy|self-awareness|self[- ]?regulation)\b/i,
  /\b(feelings|emotions|emotional|regulation|conflict|communication|compassion)\b/i,
  /\b(active listening|perspective|mindset|resilience|resilient)\b/i,
  /\b(feel|feeling|felt|mood|moods|angry|anger|sad|sadness|happy|happiness|scared|fear|worried|nervous|anxious|upset|frustrated|jealous|guilty|shame|confused|lonely|rejected)\b/i,
  /\b(empathize|empathetic|understand|understanding|relate|relating|social skills|interpersonal|self[- ]?control|impulse|temper|patience)\b/i,
];

const FINANCIAL_LITERACY_INTENT_PATTERNS = [
  /\b(finance|financial|money|budget|saving|expense)\b/i,
  /\b(bank|interest|credit|debt|loan|tax)\b/i,
  /\b(investment|mutual fund|stock|compound)\b/i,
];

function matchesAny(text, patterns) {
  return patterns.some((pattern) => pattern.test(text));
}

/** Replies to “Would you like to know more?” style prompts — no domain words, but in-session continuation. */
function isShortDialogContinuation(text) {
  const q = String(text || "").trim();
  if (!q || q.length > 120) return false;
  const low = q
    .toLowerCase()
    .replace(/\s+/g, " ")
    .replace(/[!?.]+$/g, "")
    .trim();
  const twoWord = new Set([
    "yes please",
    "go on",
    "go ahead",
    "of course",
    "no thanks",
    "no thank you",
    "not now",
    "that's all",
    "tell me more",
    "i would",
    "id like",
    "i'd like",
  ]);
  if (twoWord.has(low)) return true;
  const oneWord = new Set([
    "yes",
    "no",
    "yeah",
    "yep",
    "yup",
    "sure",
    "ok",
    "okay",
    "please",
    "continue",
    "more",
    "absolutely",
    "alright",
    "nope",
    "nah",
  ]);
  if (oneWord.has(low)) return true;
  if (/^(yes|yeah|sure)\s+please$/i.test(low)) return true;
  return false;
}

export function isReligiousTopicAllowedByIntent(text) {
  const q = String(text || "").trim();
  if (!q) return false;

  if (matchesAny(q, ALWAYS_ALLOWED_INTENT_PATTERNS)) return true;
  if (matchesAny(q, FOLLOW_UP_CONTINUATION_PATTERNS)) return true;
  if (isShortDialogContinuation(q)) return true;
  if (matchesAny(q, CLEAR_OFF_TOPIC_INTENT_PATTERNS)) return false;
  if (matchesAny(q, RELIGIOUS_INTENT_PATTERNS)) return true;

  // Permissive: allow queries that don't match any off-topic pattern.
  // The bot's own LLM guardrails will handle fine-grained scope decisions.
  return true;
}

export function isEducationTopicAllowedByIntent(text) {
  const q = String(text || "").trim();
  if (!q) return false;

  if (matchesAny(q, ALWAYS_ALLOWED_INTENT_PATTERNS)) return true;
  if (matchesAny(q, FOLLOW_UP_CONTINUATION_PATTERNS)) return true;
  if (isShortDialogContinuation(q)) return true;
  if (matchesAny(q, CLEAR_OFF_TOPIC_INTENT_PATTERNS)) return false;
  if (matchesAny(q, EDUCATION_INTENT_PATTERNS)) return true;

  // Permissive: allow queries that don't match any off-topic pattern.
  return true;
}

/**
 * Permissive intent filter shared by all domain bots.
 * Only blocks clearly off-topic queries (sports, stocks, code, etc.).
 * Allows everything else through to the bot's LLM guardrails for nuanced evaluation.
 */
function _isTopicAllowedByPatterns(text, patterns) {
  const q = String(text || "").trim();
  if (!q) return false;

  if (matchesAny(q, ALWAYS_ALLOWED_INTENT_PATTERNS)) return true;
  if (matchesAny(q, FOLLOW_UP_CONTINUATION_PATTERNS)) return true;
  if (isShortDialogContinuation(q)) return true;
  if (matchesAny(q, CLEAR_OFF_TOPIC_INTENT_PATTERNS)) return false;
  if (matchesAny(q, patterns)) return true;

  // Permissive: allow queries that don't match any off-topic pattern.
  // The bot's own LLM guardrails will handle fine-grained scope decisions.
  return true;
}

export function isDigitalLiteracyTopicAllowedByIntent(text) {
  return _isTopicAllowedByPatterns(text, DIGITAL_LITERACY_INTENT_PATTERNS);
}

export function isDesignThinkingTopicAllowedByIntent(text) {
  return _isTopicAllowedByPatterns(text, DESIGN_THINKING_INTENT_PATTERNS);
}

export function isWellbeingTopicAllowedByIntent(text) {
  const q = String(text || "").trim();
  if (!q) return false;

  // Always allow greetings, follow-ups, and dialog continuations
  if (matchesAny(q, ALWAYS_ALLOWED_INTENT_PATTERNS)) return true;
  if (matchesAny(q, FOLLOW_UP_CONTINUATION_PATTERNS)) return true;
  if (isShortDialogContinuation(q)) return true;

  // Block only clearly off-topic queries (sports, stocks, code, etc.)
  if (matchesAny(q, CLEAR_OFF_TOPIC_INTENT_PATTERNS)) return false;

  // If the query matches wellbeing keywords, definitely allow
  if (matchesAny(q, WELLBEING_INTENT_PATTERNS)) return true;

  // For wellbeing, be PERMISSIVE: allow queries that don't match any
  // off-topic pattern. The bot's own LLM guardrails will handle nuance.
  // This avoids false-positive rejections for natural emotional expressions
  // like "I had a bad day", "nobody likes me", "I can't focus", etc.
  return true;
}

export function isSustainabilityTopicAllowedByIntent(text) {
  return _isTopicAllowedByPatterns(text, SUSTAINABILITY_INTENT_PATTERNS);
}

export function isGlobalCitizenshipTopicAllowedByIntent(text) {
  return _isTopicAllowedByPatterns(text, GLOBAL_CITIZENSHIP_INTENT_PATTERNS);
}

export function isEntrepreneurshipTopicAllowedByIntent(text) {
  return _isTopicAllowedByPatterns(text, ENTREPRENEURSHIP_INTENT_PATTERNS);
}

export function isEmotionalIntelligenceTopicAllowedByIntent(text) {
  return _isTopicAllowedByPatterns(text, EMOTIONAL_INTELLIGENCE_INTENT_PATTERNS);
}

export function isFinancialLiteracyTopicAllowedByIntent(text) {
  return _isTopicAllowedByPatterns(text, FINANCIAL_LITERACY_INTENT_PATTERNS);
}
