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
{% for pub in sorted_pubs reversed %}
{% if pub.type == "arxiv" %}
<li>{{ pub.citation | markdownify }}{% if pub.paperurl %} <a href="{{ pub.paperurl }}" target="_blank">Access paper</a>{% endif %}</li>
{% endif %}
{% endfor %}
</ol>

## Publications

<ol>
{% for pub in sorted_pubs reversed %}
{% if pub.type == "published" %}
<li>{{ pub.citation | markdownify }}{% if pub.paperurl %} <a href="{{ pub.paperurl }}" target="_blank">Access paper</a>{% endif %}</li>
{% endif %}
{% endfor %}
</ol>