---
layout: archive
title: ""
permalink: /publications/
author_profile: true
---

<style>
.pub-list { padding-left: 0; list-style: none; }
.pub-list li { margin-bottom: 1rem; }
.pub-list ol { padding-left: 0; list-style: none; }
.pub-citation { font-style: normal; }
.pub-citation em { font-style: italic; }
.pub-link { margin-left: 0.5rem; }
</style>

You can find all of my works on [arXiv](http://arxiv.org/a/muller_j_3).

{% assign sorted_pubs = site.publications | sort: "date" | reverse %}

## Preprints

<ol class="pub-list" style="list-style: none; padding-left: 0;">
{% for pub in sorted_pubs %}
{% if pub.type == "arxiv" %}
<li><span class="pub-citation">{{ sorted_pubs[forloop.index].citation }}</span> {% if sorted_pubs[forloop.index].paperurl %}<a href="{{ sorted_pubs[forloop.index].paperurl }}" target="_blank">Access paper</a>{% endif %}</li>
{% endif %}
{% endfor %}
</ol>

## Publications

<ol class="pub-list" style="list-style: none; padding-left: 0;">
{% for pub in sorted_pubs %}
{% if pub.type == "published" %}
<li><span class="pub-citation">{{ sorted_pubs[forloop.index].citation }}</span> {% if sorted_pubs[forloop.index].paperurl %}<a href="{{ sorted_pubs[forloop.index].paperurl }}" target="_blank">Access paper</a>{% endif %}</li>
{% endif %}
{% endfor %}
</ol>