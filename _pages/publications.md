---
layout: archive
title: ""
permalink: /publications/
author_profile: true
---

You can find all of my works on [arXiv](http://arxiv.org/a/muller_j_3).

{% assign sorted_pubs = site.publications | sort: "date" | reverse %}

## Preprints

<ol>
{% for pub in sorted_pubs %}
{% if pub.type == "arxiv" %}
<li value="{{ forloop.rindex }}">{{ sorted_pubs[forloop.index].citation | markdownify }} {% if sorted_pubs[forloop.index].paperurl %}<a href="{{ sorted_pubs[forloop.index].paperurl }}" target="_blank">Access paper</a>{% endif %}</li>
{% endif %}
{% endfor %}
</ol>

## Publications

<ol>
{% for pub in sorted_pubs %}
{% if pub.type == "published" %}
<li value="{{ forloop.rindex }}">{{ sorted_pubs[forloop.index].citation | markdownify }} {% if sorted_pubs[forloop.index].paperurl %}<a href="{{ sorted_pubs[forloop.index].paperurl }}" target="_blank">Access paper</a>{% endif %}</li>
{% endif %}
{% endfor %}
</ol>