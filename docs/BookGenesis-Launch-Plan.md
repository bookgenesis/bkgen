# BookGenesis 1.0 Launch Plan

**Release cycle: 4 weeks.** That's short enough to make it feel like progress is happening, but long enough to allow me to take care of all the other business that has to be done each month.

*   **2017-03-28**: [Beta 1 — “MVP”](#user-content-beta-1--mvp)
*   **2017-04-25**: [Beta 2 — Subscriptions](#user-content-beta-2--subscriptions)
*   ...
*   **2017-?-?**: [Release 1.0.0](#user-content-release-100)

## Beta 1 — “MVP”

**User: “I want to be able to build a clean, publication-ready ebook from my manuscript.”**

**Summary:** Users can sign up and create one free project in their account that is limited to 10 MB. Content can be imported in Word, Markdown, and HTML; outputs can be built as .zip, .epub, and .mobi. No support yet for InDesign formats or PDF. The only interface for input and output are upload and download — no Dropbox or other file sharing integration yet. There is also no payment processing as yet, so we limit people to the one free project for this beta. 

-   **User**:
    +   Sign up → create account
    +   Login / Logout 
    -   Reset password
    +   User can own one account
-   **Account**:
    +   Free account 
    -   1 project limit, 10 MB limit
    -   Every account on its own subdomain
-   **Project**:
    -   Import content: 
        - .docx	
        - .icml
        - .idml 
        - images 
    -   Import via upload form
        - ClamAV on all
        - Linux Malware Detect on all
    -   View digital TOC
    -   Browse content
    -   View / edit project metadata
    -   Build output: 
        -   .epub
        -   .mobi
        -   .zip (project archive)
    -   Export outputs via download
-   **Word**: 
    -   provide a Word template, Manuscript.dotm, that can be used for styling a manuscript. This template includes all the basic styles needed for a book, and a content template to get started with.
-   **Documentation**:
    -   *Editing with Style* — a free ebook (hosted on my account) that explains how to use Word effectively to create a publication-ready manuscript.
    -   Online help for bookgenesis.com.

All imported content will have to be thoroughly vetted to ensure that there are no viruses / trojans / exploits embedded. Making sure that this is so is going to be one of the main activities of the private beta period.

One of my principles is, *Never include for free what you will later charge for. Whatever you do for free, keep it free. Charge for added features.* This requires only making free what you can sustain as free up to a fairly substantial scale.

I believe that a 10 MB free account is sustainable. A single Linode 2048 instance costs $10/mo. I currently have one dedicated to bookgenesis.com, in which the /home folder is a disk with 20GB free. So I can support 2,000 free users on this server before I start scaling it up. Each receives their own home directory and system user (without the ability to log in to the system, however).

Very soon I will add a subscription option, charging perhaps $5/mo. or $50/yr. per project (with volume discounts for larger numbers of projects). When we have 5 paid projects, we can put them on their own Linode and start scaling that up.

## Beta 2 — Subscriptions

**User: “I want to be able to do all of my ebook production through my bookgenesis.com account, and I'm ready to pay for that service.”**

-   More Import Formats
        - .html 
        - .epub 
        - InDesign package zip
        - bookgenesis project zip
        - .zip of the above
-   Per-Project Subscriptions

In order to enable higher-order use of the service, subscriptions will need to be enabled. This is also a good moment at which to create the first beta, signifying feature-complete for v. 1.0.0. Subscriptions require payment processing (through Stripe), subscription management, and resource management.

## Beta 2…N — ?

**User: I want the service to do Y that it doesn't do, and that feature is a must-have for me to use it.**

We don't yet know exactly what users are going to want in the first release version of the product, but we need to be prepared to respond to their requests in a timely way!

## Release 1.0.0

Release launch. PR. Event.

## Dropbox Integration

**User: “I want to be able to import project files from Dropbox and work on my project files in the Dropbox folder, automatically syncing with my bookgenesis account.”**

This is the input/output model that I myself will use the most! And it seems that most of the publishing industry is using Dropbox for file sharing. So this is a necessary component.

*   **Content import via Dropbox link.** This will import the content into the active / a new project from the files in the link. It will not "join" a shared folder but create a new one.
*   **Shared Dropbox folder per Project.** The project’s files will be a Dropbox folder that is shared between the server and the user. This allows the user to add / edit files to the project on the desktop via the shared folder. It also allows the user to share their project with others via Dropbox sharing.
*   **Automatic syncing.** Changes made to the Dropbox folder are reflected in the online account. *This requires building an automatic monitoring or hook interface between the Dropbox folder and the database, in order to keep the database up-to-date with the project folder.*

All automatically synced content will have to be vetted when synced, using the same procedures that are used on uploaded content, to ensure that no security breach can be introduced through that path.

I've gone back and forth on whether the shared Dropbox folder should be per-Account or per-Project. I originally thought I would make the Account, rather than the Project, a shared Dropbox folder. Per-Account would be a convenience for users, because they could simply add folders, work on them locally, and then "turn on" those folders on the server when they were ready to. That's also a nice way to make it easy for them to add projects to their account — and to give us more revenue! But there are several reasons not to do it this, but to make the Dropbox folders per-Project. (1) An Account doesn't always share all its Projects with the same people; this way, we can have a different team on every project. (But is that really the most common use case? It seems to me that every team could have its own account, with all the projects in that account). (2) Similarly, a user's access rights on a shared Dropbox folder are global to that folder — if they can edit the folder, they can edit any subfolder, which is to say, any project within that account folder. Not always do all members of the team have the same rights across all projects that the team does. (3) Adding a folder to an account on the desktop shouldn't result in those files being added to the account folder on the server. Though we could exclude them until they were added as projects to the account. — At the end of the day, it seems that per-Account Dropbox folders would be more convenient for users, but that per-Project Dropbox folders provide a more flexible and long-term-robust solution, if a little less convenient for users. How do we resolve this? 

One solution: **Start with per-Project shared folders, then later (if needed) add an Account-level option to make Dropbox folder sharing either per-Account or per-Project within that Account.** This solution keeps things simple at the beginning, and simplicity also aligns with long-term flexibility. Per-Account also seems like an enterprise-level feature: We could make that available to users who are willing to pay more for an enterprise account, which will also include things like multi-user and multi-team management.

