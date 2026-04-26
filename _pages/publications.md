---
layout: archive
title: ""
permalink: /publications/
author_profile: true
---

You can find all of my works on [arXiv](http://arxiv.org/a/muller_j_3).

{% assign sorted_pubs = site.publications | sort: "date" | reverse %}

## Preprints

{% assign total_arxiv = 0 %}
{% for pub in sorted_pubs %}
{% if pub.type == "arxiv" %}
{% assign total_arxiv = total_arxiv | plus: 1 %}
{% endif %}
{% endfor %}

<ol start="{{ total_arxiv }}">
{% for pub in sorted_pubs %}
{% if pub.type == "arxiv" %}
<li>{{ pub.citation | markdownify }}{% if pub.paperurl %}<a href="{{ pub.paperurl }}" target="_blank">Access paper</a>{% endif %}</li>
{% endif %}
{% endfor %}
</ol>

## Publications

{% assign total_published = 0 %}
{% for pub in sorted_pubs %}
{% if pub.type == "published" %}
{% assign total_published = total_published | plus: 1 %}
{% endif %}
{% endfor %}

<ol start="{{ total_published }}">
{% for pub in sorted_pubs %}
{% if pub.type == "published" %}
<li>{{ pub.citation | markdownify }}{% if pub.paperurl %}<a href="{{ pub.paperurl }}" target="_blank">Access paper</a>{% endif %}</li>
{% endif %}
{% endfor %}
</ol>