The hashtree_processor.py utility takes the output of the
hashtree dumps, and uses that to either create MOs in APIC,
or resources in the AIM DB. The AIM DB resources are created
using the system ID of the installed setup. The APIC MOs are
created using a user-specified annotation value, or the default
annotation value of None.

The processor gets the data from an AIM hashtree dump.
The commands should be run from inside the aim container:

<pre><code>$ aimctl hashtree dump -t tn-prj_4cafd4b9773c4649a497f72d5ca600be -f configured > configured-tree.txt
$ aimctl hashtree dump -t tn-prj_4cafd4b9773c4649a497f72d5ca600be -f monitored > monitored-tree.txt
</code></pre>

Alternatively, you can dump all of the hash trees of each type:
<pre><code>$ aimctl hashtree dump -f configured > all-configu-trees.txt
$ aimctl hashtree dump -f monitored > all-monitored-trees.txt
</code></pre>

You can then use the split_trees.py script to split the trees into separate files:
<pre><code>$ ptyhon  split_files.py -t configured -f all-configu-trees.txt
$ ptyhon  split_files.py -t monitored -f all-monitored-trees.txt
</code></pre>

These will generate files of the name <tenant>.config and <tenant>.monitor.

You then can use the hashtree_process.py script to create resources in
the AIM DB or MOs in APIC, using the hashtree dumps. To create objects ini
the AIM DB from the configured-tree.txt file:
<pre><code>$ python hashtree_processor.py -f configured-tree.txt  -d
</code></pre>

Similarly, to create MOs in APIC from the monitored-tree.txt file:
<pre><code>$ python hashtree_processor.py -f monitored-tree.txt -a
</code></pre>

Keep in mind that in order to push the monitored tree objects to ACI,
the configured tree objects should be pushed first. Also, you may need
to manually create the tenants (I've seen cases where the tenant doesn't
get created, even though the hashtree should have created it in the DB).
