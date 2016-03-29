;; -*-emacs-lisp-*-
;;
;; Emacs startup file, e.g.  /etc/emacs/site-start.d/50lophi-disk-introspection-server.el
;; for the Debian lophi-disk-introspection-server package
;;
;; Originally contributed by Nils Naumann <naumann@unileoben.ac.at>
;; Modified by Dirk Eddelbuettel <edd@debian.org>
;; Adapted for dh-make by Jim Van Zandt <jrv@debian.org>

;; The lophi-disk-introspection-server package follows the Debian/GNU Linux 'emacsen' policy and
;; byte-compiles its elisp files for each 'emacs flavor' (emacs19,
;; xemacs19, emacs20, xemacs20...).  The compiled code is then
;; installed in a subdirectory of the respective site-lisp directory.
;; We have to add this to the load-path:
(let ((package-dir (concat "/usr/share/"
                           (symbol-name flavor)
                           "/site-lisp/lophi-disk-introspection-server")))
;; If package-dir does not exist, the lophi-disk-introspection-server package must have
;; removed but not purged, and we should skip the setup.
  (when (file-directory-p package-dir)
    (setq load-path (cons package-dir load-path))
    (autoload 'lophi-disk-introspection-server-mode "lophi-disk-introspection-server-mode"
      "Major mode for editing lophi-disk-introspection-server files." t)
    (add-to-list 'auto-mode-alist '("\\.lophi-disk-introspection-server$" . lophi-disk-introspection-server-mode))))

