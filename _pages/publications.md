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
<li>
{{ pub.citation }} {% if pub.paperurl %}[Access paper]({{ pub.paperurl }}){% endif %}
</li>
{% endif %}
{% endfor %}
</ol>

## Publications

<ol>
{% for pub in sorted_pubs %}
{% if pub.type == "published" %}
<li>
{{ pub.citation }} {% if pub.paperurl %}[Access paper]({{ pub.paperurl }}){% endif %}
</li>
{% endif %}
{% endfor %}
</ol>