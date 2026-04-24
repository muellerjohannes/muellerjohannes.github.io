---
layout: archive
title: ""
permalink: /publications/
author_profile: true
---

You can find all of my works as preprints on [arXiv](http://arxiv.org/a/muller_j_3).

{% assign publications = site.publications | sort: "date" | reverse %}
{% for pub in publications %}
{{ pub.citation }}
{% endfor %}