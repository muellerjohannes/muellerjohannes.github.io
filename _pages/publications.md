---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
---
You can find these publications on my <u><a href="https://scholar.google.de/citations?user=cnSjMBwAAAAJ&hl=en">google scholar profile</a>.

---
{% include base_path %}

{% for post in site.publications reversed %}
  {% include archive-single.html %}
{% endfor %}
