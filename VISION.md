# PCSS Alumni Website Vision

## Purpose

The PCSS Alumni website should be more than an archive. Its purpose is to help
former students reconnect, participate in the alumni community and create new
opportunities for current students.

The historical archive remains one of the site's strongest assets, but it should
support a larger community experience rather than define the whole experience.

## Positioning

> Reconnect with Port Credit. Give back to what comes next.

The site should invite alumni from every decade to attend events, volunteer,
mentor, support scholarships and school projects, and explore the memories that
connect the community.

## Visitor goals

A first-time visitor should immediately understand that they can:

- join or update their alumni information;
- attend the annual Alumni Night and smaller community events;
- volunteer time, expertise or resources;
- mentor students, speak at the school or support co-op opportunities;
- contribute to scholarships and school initiatives;
- browse yearbooks, photographs, reunion history and alumni stories.

## Proposed navigation

1. **Home**
2. **Events**
3. **Get Involved**
4. **Impact**
5. **Memories**
6. **About**
7. **Join the Community**, presented as the primary navigation action

The detailed historical archive can remain accessible through Memories and the
site footer.

## Homepage experience

### 1. Emotional introduction

Lead with a strong alumni, event or school photograph and a direct invitation.

**Headline:** Reconnect with Port Credit. Give back to what comes next.

**Supporting message:** Join alumni from every decade for events, mentoring,
school projects, scholarships and the memories that connect us.

Primary actions:

- Join the alumni community
- Alumni Night, May 2027
- Explore the yearbooks

### 2. Annual Alumni Night

The annual Alumni Night should be the first major feature after the hero. Until
the event details are confirmed, the page should show May 2027 with the date and
venue marked as pending.

This section should include:

- a photograph from a previous Alumni Night;
- a short explanation of the event;
- a button to receive registration updates;
- links to photographs and stories from previous events.

Once the date and venue are confirmed, this becomes the primary event
registration experience.

### 3. Ways to participate

Present four clear options:

- **Attend** alumni events and gatherings
- **Volunteer** for events and school projects
- **Mentor** students or speak about a career or area of expertise
- **Support** scholarships and school initiatives

Each option can lead to the same alumni interest form.

### 4. Scholarships and impact

The site should show what alumni support makes possible, not only list recipient
names. Feature a small number of current stories and retain the complete
historical tables below them.

Useful content includes:

- a featured scholarship recipient;
- an alumni-supported school improvement;
- a current student opportunity;
- photographs and short first-person stories;
- links to the full scholarship and project records.

No testimonial, statistic or personal story should be published without a
verified source and appropriate permission.

### 5. Community events

Provide a simple area for smaller gatherings throughout the year, including:

- social events;
- networking and career events;
- mentoring activities;
- school activities;
- volunteer opportunities.

When there are no scheduled events, invite alumni to help organize the next one
instead of showing an empty calendar.

### 6. Memories

Create a visually rich gateway to:

- the 69 preserved yearbooks;
- Alumni Night and reunion photographs;
- alumni memories and feature stories;
- school history;
- historical association records.

The archive should be easy to explore by decade and content type.

### 7. Final invitation

End major pages with a consistent community invitation:

> Port Credit's alumni community is what we make it.

Actions:

- Join or update my details
- Offer to help

## Alumni registration form

Create one Google Form called **Join the PCSS Alumni Community**, owned by
Andrew's personal Google account. Add another trusted Alumni Association member
as an editor when appropriate so the form does not depend on a single person.

Recommended fields:

- full name;
- preferred email address;
- graduation year;
- relationship to PCSS, such as student, staff or community member;
- current city or region;
- interests, using checkboxes:
  - Alumni Night;
  - smaller social events;
  - receiving updates;
  - volunteering;
  - mentoring;
  - guest speaking;
  - hiring or supporting co-op students;
  - scholarships and fundraising;
  - school projects;
  - contributing photographs or stories;
- skills, experience or resources the person might offer;
- optional message;
- consent to receive PCSS Alumni communications.

Responses should be stored in a private Google Sheet with restricted access.
The form should explain how the information will be used and how someone can
request removal.

The website should link to the form rather than embed it. A normal link is
simpler, works with the site's strict Content Security Policy and avoids adding
an external frame to every page.

Event-specific RSVP forms can be added later when dates, venues and capacity are
known. The master form remains the single place for general registration and
interest preferences.

## Page responsibilities

| Page | Primary purpose |
| --- | --- |
| Home | Introduce the community, feature Alumni Night and provide clear calls to action |
| Events | Present Alumni Night first, smaller gatherings second, and past events below |
| Get Involved | Explain volunteering, mentoring, speaking, co-op, project and support opportunities |
| Impact | Tell scholarship, student and school-improvement stories, with full records available |
| Memories | Bring together yearbooks, photographs, reunions, stories and school history |
| About | Explain the mission, committee, relationship to the school and governance |
| Join | Introduce and link to the master Google Form |

## Content needed

Before completing the community-focused redesign, collect:

- the confirmed Alumni Night date, venue and organizer;
- three to five strong event photographs;
- two or three scholarship recipient stories with permission;
- photographs of alumni-supported school improvements;
- current school priorities where alumni can help;
- current committee roles and a general contact address;
- an approved donation destination and confirmation of whether tax receipts are
  available.

Until an official donation process is approved, financial-support calls to
action should lead to an expression-of-interest option in the form rather than
accepting payments.

Photographs or stories involving current students should only be published with
appropriate permission.

## Implementation approach

The site should remain a static Quarto website hosted on GitHub Pages. Public
pages remain editable as `.qmd` files. Simple structured files such as
`data/events.yml` and `data/impact.yml` can be introduced so recurring updates
do not require redesigning page markup.

The existing recovered pages should be retained and reorganized beneath the new
community navigation. Historical source material should not be deleted simply
because it is no longer part of the primary visitor journey.

## Rollout

### Phase 1: Community foundation

- redesign the homepage around participation;
- revise the navigation;
- feature the annual Alumni Night;
- create and connect the master Google Form;
- add Get Involved and Memories landing pages;
- place consistent calls to action throughout the site.

### Phase 2: Impact and storytelling

- publish scholarship recipient features;
- document alumni-supported school improvements;
- add stronger event photography;
- publish current student and alumni profiles with permission.

### Phase 3: Ongoing community programme

- publish smaller event listings;
- add event-specific RSVP forms where needed;
- promote mentoring, speaking and co-op opportunities;
- establish a regular content-update rhythm;
- open annual Alumni Night registration when details are confirmed.

## Measures of success

Initial measures can remain simple and privacy-conscious:

- alumni form registrations;
- Alumni Night interest and registrations;
- volunteers and mentors identified;
- participation in smaller events;
- offers of speaking, co-op or project support;
- scholarship and impact stories published;
- visits to yearbooks and other memory collections.

The first version does not require advertising trackers or a complex membership
system. Google Form responses and event participation are enough to determine
whether the site is helping rebuild an active alumni community.

