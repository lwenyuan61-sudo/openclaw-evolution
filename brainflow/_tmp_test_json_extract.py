from plugins._json_extract import extract_first_json_object

samples = [
  '{"a": 1}',
  'noise before {"a": 1} noise after',
  '```json\n{"a": 1,}\n```',
  '[1,2,3]',
]
for s in samples:
  print('IN:',s)
  print('OUT:',extract_first_json_object(s))
  print('---')
