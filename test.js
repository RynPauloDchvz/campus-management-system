const raw = '"[{\\"id\\": 1, \\"name\\": \\"test\\"}]"';
console.log('raw:', raw);
let parsed = raw.startsWith('"') ? JSON.parse(raw) : raw;
console.log('parsed (first):', typeof parsed, parsed);
let finalParsed = typeof parsed === 'string' ? JSON.parse(parsed) : parsed;
console.log('final:', typeof finalParsed, finalParsed[0].name);
