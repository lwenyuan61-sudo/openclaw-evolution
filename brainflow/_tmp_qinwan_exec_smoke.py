from plugins.qinwan_execute.plugin import run

# Smoke test offline path only
print(run({
  'kind':'subgoal',
  'id':'smoke1',
  'topic':'longevity',
  'stage':'reflect',
  'title':'smoke offline',
  'next':'append one line',
  'needs_network': False,
}, semantic_text=''))
