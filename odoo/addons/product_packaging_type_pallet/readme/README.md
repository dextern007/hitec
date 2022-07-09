# Project C2C Migration information

**please, UPDATE ME!**

_Odoo 13.0 project generated by phuctran, 2020-10-30 00:09:51_

# Checklist

- [ ] Update oca_dependencies.txt
- [ ] Update test-requirements.txt
- [ ] Push code to trobz repo (use the script `deploy.sh`, ie:
      `./deploy.sh stock-logistics-workflow stock_partner_delivery_window`)

# Notes

## Preserving commit history of a PR

This case is done when the given module has PR but not merged yet. For example:

- Module: `sale_partner_cutoff_delivery_window`
- PR: 1377 on v13
- Migration: v14

```sh
git clone https://github.com/OCA/sale-workflow -b 14.0
git fetch origin pull/1377/head:13.0_pr1377
git checkout -b 14.0-mig-sale_partner_cutoff_delivery_window origin/14.0
git format-patch --keep-subject --stdout origin/14.0..13.0_pr1377 -- sale_partner_cutoff_delivery_window | git am -3 --keep
```