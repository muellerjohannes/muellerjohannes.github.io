---
layout: archive
title: ""
permalink: /publications/
author_profile: true
---

You can find all of my works as preprints on [arXiv](http://arxiv.org/a/muller_j_3).

{% assign sorted_pubs = site.publications | sort: "date" %}

## Preprints

<ol reversed>
{% for pub in sorted_pubs %}
{% if pub.type == "arxiv" %}
<li>
{{ pub.citation }} {% if pub.paperurl %}[Access paper]({{ pub.paperurl }}){% else %}[Google Scholar](https://scholar.google.com/scholar?q={{ pub.title | url_encode }}){% endif %}
</li>
{% endif %}
{% endfor %}
</ol>

## Publications

<ol reversed>
{% for pub in sorted_pubs %}
{% if pub.type == "published" %}
<li>
{{ pub.citation }} {% if pub.paperurl %}[Access paper]({{ pub.paperurl }}){% else %}[Google Scholar](https://scholar.google.com/scholar?q={{ pub.title | url_encode }}){% endif %}
</li>
{% endif %}
{% endfor %}
</ol>